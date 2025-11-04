import streamlit as st
import json
import boto3
import os 

Base = os.path.abspath(".")

# === AWS Configuration === #
COGNITO_REGION = "ap-southeast-2"
BEDROCK_REGION = "ap-southeast-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
IDENTITY_POOL_ID = "ap-southeast-2:eaa059af-fd47-4692-941d-e314f2bd5a0e"
USER_POOL_ID = "ap-southeast-2_NfoZbDvjD"
APP_CLIENT_ID = "3p3lrenj17et3qfrnvu332dvka"
USERNAME = "s4167911@student.rmit.edu.au" 
PASSWORD = "epS4wJ$^3qFGADEBEKCB" 


# === Helper: Get AWS Credentials === #
def get_credentials(username, password):
    idp_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    response = idp_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
        ClientId=APP_CLIENT_ID,
    )
    id_token = response["AuthenticationResult"]["IdToken"]

    identity_client = boto3.client("cognito-identity", region_name=COGNITO_REGION)
    identity_response = identity_client.get_id(
        IdentityPoolId=IDENTITY_POOL_ID,
        Logins={f"cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}": id_token},
    )

    creds_response = identity_client.get_credentials_for_identity(
        IdentityId=identity_response["IdentityId"],
        Logins={f"cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}": id_token},
    )

    return creds_response["Credentials"]


# === Helper: Build Prompt from JSON + Structure === #
def build_prompt(courses, user_question, faqs, stcon, prompt_mem, structure=None): 
    #Retrieving frequently asked question data
    question = list()
    for questions in faqs:
        faqs_title = questions.get("question", "Untitled")
        answer = questions.get("answer", "Not given")
        qanda_text = f'Question: {faqs_title} Answer: {answer}'
        question.append(qanda_text)
    full_faqs = "\n".join(question)
    #Retrieving student connect contact info
    studentconnect = list()
    for links in stcon:
        title = links.get("info", "Other")
        link = links.get("link", "https://rmit.edu.au")
        connect_text = f'Help type {title}, Link {link}'
        studentconnect.append(connect_text)
    full_connect = "\n".join(studentconnect)
    #Retrieving course data
    course_list = []
    for course in courses:
        title = course.get("course", "Untitled")
        atar_req = course.get("atar", "N/A")
        campus = course.get("campus", "Unknown")
        fulltime_duration = course.get("ftduration", "N/A")
        parttime_duration = course.get("ptduration", "N/A")
        fee_type = course.get("feetype", "Unknown")
        fee_amount = course.get("feeamount", "Check with link")
        next_intake = course.get("Nextintake", "N/A")
        year_1_courses = course.get("y1courses", [])
        year_2_courses = course.get("y2courses", [])
        year_3_courses = course.get("y3courses", [])
        minor_courses = course.get("othercourses", [])
        link = course.get("link", "https://rmit.edu.au")
        course_text = f"- {title} {campus}, {atar_req} Time: ({fulltime_duration}, {parttime_duration}), Fees: {fee_amount}, Next intake: {next_intake} Courses:\n({year_1_courses})\n({year_2_courses})\n({year_3_courses})\n Minors:({minor_courses})\n Links {link}"
        course_list.append(course_text)
    full_course_context = "\n".join(course_list)
    #Creating prompt to be sent to processed
    prompt = (
        "You are a helpful assistant that supports new and future students by helping them"
        + "Select courses that fit given specifications, compare courses and answer frequently asked questions"
        + f'Frequently asked questions {full_faqs}'
        + "\n\nUser:\n" + user_question
        + f'If you are unsure of the answer to a question you will reference the student to {full_connect} that best relates to their question'
        + f'Courses available at RMIT currently {full_course_context}\n'
    )

# === Helper: Invoke Claude via Bedrock === #
def invoke_bedrock(prompt_text, max_tokens=640, temperature=0.3, top_p=0.9):
    credentials = get_credentials(USERNAME, PASSWORD)

    bedrock_runtime = boto3.client(
        "bedrock-runtime",
        region_name=BEDROCK_REGION,
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretKey"],
        aws_session_token=credentials["SessionToken"],
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "messages": [{"role": "user", "content": prompt_text}]
    }

    response = bedrock_runtime.invoke_model(
        body=json.dumps(payload),
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

# === Streamlit UI === #
st.set_page_config(page_title="RMIT Advisor", layout="centered")

st.title("\U0001F393 RMIT Advisor")
st.markdown("This assistant helps students in RMIT choose courses.")

st.subheader("Ask a question")
user_question = st.text_input(
    "\U0001F4AC What would you like to ask?",
    placeholder="e.g., I'm a second-year student interested in digital forensics and blockchain."
)

if st.button("\U0001F4A1 Get Advice"):
    if not user_question:
        st.warning("Please enter a question.")
    else:
        try:
            with open(f'{Base}/allcourses.json', 'r', errors='ignore') as allc:
                courses = json.load(allc)
            with open(f'{Base}/allsubjects.json', 'r', errors='ignore') as alls:
                structure = json.load(alls)
            with open(f'{Base}/faqs.json', 'r', errors='ignore') as faqs_text:
                faqs = json.load(faqs_text)
            with open(f'{Base}/stconnect.json', 'r', errors='ignore') as stcon_text:
                stcon = json.load(stcon_text)
            prompt = build_prompt(courses, user_question, faqs, stcon, structure)

            with st.spinner("\U0001F50D Generating advice..."):
                answer = invoke_bedrock(prompt)
                st.success("\u2705 Response received")
                st.text_area("\U0001F916 Claude's Answer", answer, height=300)

        except Exception as e:
            st.error(f"\u274C Error: {str(e)}")
