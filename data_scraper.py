import os 
import requests
from bs4 import BeautifulSoup 
from xhtml2pdf import pisa
from PyPDF2 import PdfReader
import json
import re
BASE = os.path.abspath(".")

#Retrives all bachelor degrees from RMIT's sitemap 
def current_links():
    All_links = list()
    url = "https://www.rmit.edu.au/sitemap.xml"
    #Retrieves the sitemap data
    xml = requests.get(url)
    #Formats the retrieved data back to xml
    file = BeautifulSoup(xml.text, features="xml")

    #Sort all links for Bachelor degree links 
    list_file = str(file).split("loc")
    for i in list_file:
        if i[:92] == ">https://www.rmit.edu.au/study-with-us/levels-of-study/undergraduate-study/bachelor-degrees/":
            rid_of_start = i[1:]
            rid_of_end = rid_of_start[:-2]
            All_links.append(rid_of_end)
            
    #Splits all the links into applications, further study and main pages
    with open(f"{BASE}/Links/apply-now.txt", "w") as page:
        for i in All_links:
            if i[-10:] == "/apply-now":
                All_links.remove(i)
                page.write(i + "\n")
        page.close()
    with open(f"{BASE}/Links/further-study.txt", "w") as page:
        for i in All_links:
            if i[-14:] == "/further-study":
                All_links.remove(i)
                page.write(i + "\n")
        page.close()
    with open(f"{BASE}/Links/Links.txt", "w") as page:
        for i in All_links:
            if i[-24:] != "/admissions-transparency":
                page.write(i + "\n")
        page.close()

    #Seperate list for checking plans
    with open(f"{BASE}/Links/Plan_links.txt", "w") as page:
        for i in All_links:
            if i[-24:] != "/admissions-transparency":
                lesser = i[23:]
                page.write(lesser + "\n")
        page.close()

    dupe_check = list()
    links_url = list()
    complete_plan_list = list()

    #Plan links are retrieved and from each course site the course plan is retrieved
    with open(f"{BASE}/Links/Links.txt", "r") as links:
        for i in links.readlines():
            links_url.append(i.strip("\n"))
        #All links retrieved are searched for a course plan 
        for i in links_url:
            response = requests.get(i)
            soup = BeautifulSoup(response.text, 'html.parser')
            #findall and linkget basically just finds all the links in the page 
            all_a = soup.find_all('a')
            for link in all_a:
                current = link.get('href')
                #Filters out any duplicate links 
                if current not in dupe_check:
                    if str(current)[:68] == "/study-with-us/levels-of-study/undergraduate-study/bachelor-degrees/":
                        dupe_check.append(current)
                        if str(current)[-5:] == "auscy":
                            complete_plan_list.append(f'https://rmit.edu.au{current}')
    links.close()
    #All the new course plan links are put into a new file                      
    with open(f"{BASE}/Links/complete_plan_links.txt", "w") as plan:
        for i in complete_plan_list:
            plan.write(i + "\n")
        plan.close()

#Converts the site data into an pdf file 
def convert_to_pdf(url, pdf_path):
    #gets site data
    response = requests.get(url)
    #Formats site date into html text
    html_text = response.text
    #Writes the file to path
    with open(pdf_path, "wb") as pdf_file:
        #Creates the formated file using xhtml2pdf pisa formatter
        status = pisa.CreatePDF(html_text, dest=pdf_file)
    return not status.err

#Used when filtering course info as some courses contain a colon
def iscolon(x):
    if x == ":":
        return True
    else:
        return False

#Collected PDF's are filtered and provide json output 
def coursejsoninfo():
    sts = list()
    #Getting all the pdf names 
    pdf_directory = os.listdir(f'{BASE}/Raw_Files')
    #Collects relevant data from each file
    for i in pdf_directory:
        test_list = list()
        #Formats pdf back into text 
        reader = PdfReader(f"{BASE}/Raw_Files/{i}")
        for page in reader.pages:
            t = page.extract_text()
            if t:
                test_list.append(t)
        next_list = list()
        for k in test_list:
            k = k.split("\n")
            next_list.append(k) 
        #Getting all the variables to put in the json
        course = next_list[0][0]
        atar = next_list[3][20]
        Ftime = next_list[3][22]
        #Information offset by part-time, statement resets it 
        if next_list[3][23] == "Fees:":
            Ptime = "N/A"
            Feetype = next_list[3][24]
            Nextintake = next_list[3][26]
            Location = next_list[3][28]
            if next_list[3][34] == "Fees:":
                Feeamount = next_list[3][35]
            else:
                Feeamount = next_list[3][34]
        else:
            Ptime = next_list[3][23]
            Feetype = next_list[3][25]
            Feeamount = next_list[3][35]
            Nextintake = next_list[3][27]
            Location = next_list[3][29]


        #Getting link to current file 
        Link = str()
        with open(f'{BASE}/Links/complete_plan_links.txt', "r") as link:
            for p in link:
                name = p.split("/")[-1].strip()
                if i.strip(".pdf") == name:
                    Link = p.rstrip("\n")  
            #Getting the HTML
            response = requests.get(Link)
            soup = BeautifulSoup(response.text, 'html.parser')
            #Getting the div at the start and end of all the subjects
            start = soup.find("div", class_="programStructureDescription")
            end = soup.find("div", class_="modal plan-page-modal")
            all_stuff = list()
            current = start.next_sibling
            #Getting everything between start and end 
            while current != end:
                if current.name:
                    all_stuff.append(current)
                elif isinstance(current, str):
                    if current.strip():
                        all_stuff.append(current.strip())
                current = current.next_sibling
            names = list()
            y1courses = list()
            y2courses = list()
            y3courses = list()
            othercourses = list()
            partno = 0
            base_num = 0 
            #All subjects are surrounded by _blank targets and the closing html, so they are used to seperate them in the list
            for parts in all_stuff:
                names = re.split('"_blank">|</a></td><td class="cellCenter"', str(parts))
                for name in names:
                    #Sort the splited list ensuring that only subjects get through
                    if all(x.isalnum() or x.isspace() or iscolon(x) for x in name):
                        if base_num == 0:
                            if len(name) > 0:
                                base_num = partno  
                        if partno == base_num:
                            y1courses.append(name)
                        elif partno == base_num + 3:
                            y2courses.append(name)
                        elif partno == base_num + 6:
                            y3courses.append(name)
                        else:
                            othercourses.append(name)               
                partno += 1           
        #Adding all values from course into a json string
        st_file = {
            "course": course,
            "atar": atar,
            "campus": Location,
            "ftduration": Ftime,
            "ptduration": Ptime,
            "feetype": Feetype,
            "feeamount": Feeamount,
            "nextintake": Nextintake,
            "year1courses": y1courses,
            "year2courses": y2courses,
            "year3courses": y3courses,
            "othercourses": othercourses,
            "link": Link
        }
        #Saving each set of information to a list and then writing to the json
        with open("allcourses.json", 'w', encoding='utf-8') as file:
            sts.append(st_file)
            json.dump(sts, file, ensure_ascii=False, indent=4)

#Brute forces all subject links 
def subjectlinkfinder():
    all_course_links = list()
    #In general all of the courses are in the 1000 - 60000 range, but for expandability sake, it sorts through all possibilites
    pagenumber = 0
    while pagenumber < 1000000:
        soup = 0
        #All courses are 6 digits so some numbers need to be prepended with zeroes
        if len(str(pagenumber)) < 6:
            while len(str(pagenumber)) < 6:
                pagenumber = "0" + str(pagenumber)
        #Current url is made and html is collected from site 
        current_course = f"https://www.rmit.edu.au/courses/{pagenumber}"
        response = requests.get(current_course)
        soup = BeautifulSoup(response.text, 'html.parser')
        #h1 html either encompases the course title, or page not found, so everything that produces a title is saved to valid_courses
        correct = soup.find_all('h1')
        if str(correct) == "[<h1>Page not found</h1>]":
            pass
        else:
            #Course links are saved to file 
            with open(f'{BASE}/Links/valid_course.txt', "w") as vcourse:
                all_course_links.append(current_course)
                for all_course in all_course_links:
                    vcourse.write(all_course + "\n")
                print("valid found")
        pagenumber = int(pagenumber) + 1

#Saving all subject information to json
def subjectjsoninfo():
    subjects_list = list()
    with open(f'{BASE}/Links/valid_course.txt', "r") as subjects:
        for subject in subjects.readlines():
            response = requests.get(subject.strip())
            soup = BeautifulSoup(response.text, 'html.parser')
            course_title = str(str(soup.find("title")).lstrip("<title>")).rstrip("</title>")
            try:
                credit = float(str(soup.find_all("p")[1]).split("</strong>")[1].rstrip("</p>").strip())
            except ValueError:
                credit = float(str(soup.find_all("p")[2]).split("</strong>")[1].rstrip("</p>").strip())
            try:
                course_code = str(str(soup.find_all("td")[6]).lstrip("<td><p>").rstrip("</td></p>"))
            except (AttributeError, IndexError) as e:
                course_code = "Could not find"
            
            #These variables find the paragraph containing the coordinator __ text
            #This contains the values of name, phone, email and the program seperates the data
            try:
                coordinator_name = str(str(soup.select('p:-soup-contains("Course Coordinator:")')).split("</strong>")[1]).rstrip("</p>]").strip()
            #All values have an except as some pages are formatted slightly differently and may not work
            except (AttributeError, IndexError) as e:
                coordinator_name = "Could not find"
            try:
                coordinator_phone = str(str(soup.select('p:-soup-contains("Course Coordinator Phone:")')).split("</strong>")[1]).rstrip("</p>]").strip()
            except (AttributeError, IndexError) as e:
                coordinator_phone = "Could not find"
            try:
                coordinator_email = str(str(soup.select('p:-soup-contains("Course Coordinator Email:")')).split("</strong>")[1].split(">")[1].rstrip("</a"))
            except (AttributeError, IndexError) as e:
                coordinator_email = "Could not find"
            try:
                desc = soup.select('p:-soup-contains("Course Description")')[0]
                course_description = str(desc.find_next("p")).split("</p>")[0].lstrip("<p>").split("<br/>")[0].strip("</em>").strip()
            except (AttributeError, IndexError) as e:
                course_description = "Could not find"
            #Adding all values from subject into a json string
            course_file = {
                "course": course_title,
                "credits": credit,
                "code":course_code,
                "coordinator": coordinator_name,
                "phonenumber": coordinator_phone,
                "email": coordinator_email,
                "desc": course_description,
                "link": subject.rstrip("\n")
            }   
            
            #Saving each set of information to a list and then writing to the json
            with open("allsubjects.json", 'w', encoding='utf-8') as file:
                subjects_list.append(course_file)
                json.dump(subjects_list, file, ensure_ascii=False, indent=4)
    print("done")

#Retrieves all of the Q/A from the rmit faqs page 
def faqs_info():
    questions_list = list()
    url = "https://www.rmit.edu.au/study-with-us/applying-to-rmit/frequently-asked-questions#program-and-course-information"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    #All of the information we gather is within this type of div class 
    htmlquest = soup.find_all("div", class_="accordion-item rounded-0 border-start-0 border-end-0")
    for questions in htmlquest:
        #Title text are 'stored' in span tags
        title = re.split('<span>|</span>', str(questions))
        question_title = title[1]
        quest = re.split('<p>|</p>', str(questions))
        not_text = False
        letter_list = list()
        #Retrieves the text from the tagged string
        for letter in quest[1]:
            if letter == "<":
                not_text = True
            if not_text == False:
                letter_list.append(letter)
            if letter == ">":
                not_text = False
        question_answer = "".join(letter_list)
        faqs = {
            "question": question_title,
            "answer": question_answer
        }
        #Saving each set of information to a list and then writing to the json
        with open("faqs.json", 'w', encoding='utf-8') as file:
            questions_list.append(faqs)
            json.dump(questions_list, file, ensure_ascii=False, indent=4)

#Retrieves all of the links from the student connect contact website 
def connect_info():
    connect = list()
    url = "https://www.rmit.edu.au/students/support-services/student-connect"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    htmltitle = soup.find_all("div", class_="aem-Grid aem-Grid--4 aem-Grid--default--4 aem-Grid--phone--6")
    for titles in htmltitle:
        title_split = re.split('<h4 style="text-align: center;">|</h4>', str(titles))
        title = title_split[1]
        found = titles.find("a")
        link_split = re.split('"link": "|",', str(found))
        
        student_con_info = {
            "info": title,
            "link": link_split[4]
        }
        #Saving each set of information to a list and then writing to the json
        with open("stconnect.json", 'w', encoding='utf-8') as file:
            connect.append(student_con_info)
            json.dump(connect, file, ensure_ascii=False, indent=4)

#These are quick to update so they can do so without user permission
faqs_info()
connect_info()

yn = input("Do you want to get all current courses? Y/N").upper()
if yn == "Y":
   current_links()
else:
    pass
    
tf = input("Do you want to update the course plans? Y/N").upper()
if tf == "Y":
    list_of_dirs = list()
    with open(f"{BASE}/Links/complete_plan_links.txt", "r") as plan:
        lines = plan.readlines()
        for i in lines:
            i = i.rstrip("\n")
            name = i.split("/")[-1]
            pdf_path = f"{BASE}/Raw_Files/{name}.pdf"
            convert_to_pdf(i, pdf_path)  
else:
    pass

ci = input("Do you want to update the course database? Y/N").upper()
if ci == "Y":
    coursejsoninfo()
else:
    pass

lf = input("Do you want to update the subject link database? (This will take a very long time) Y/N").upper()
if lf == "Y":
    subjectlinkfinder()
else:
    pass

si = input("Do you want to update the subject database? (This will take a very long time) Y/N").upper()
if si == "Y":
    subjectjsoninfo()
else:
    pass



