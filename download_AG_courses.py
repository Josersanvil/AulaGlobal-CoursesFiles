try:
    # For Python 3.0 and later
    import urllib.request as urllib_req
except ImportError:
    # Fall back to Python 2's urllib_req
    import urllib2 as urllib_req 

import json
import os
import argparse
import xml.etree.ElementTree as et



domain = 'aulaglobal.uc3m.es'
webservice = '/webservice/rest/server.php'
service = 'ag_mobile'


# First we need the token

def get_token(user, passwd):
    url_token = 'https://' + domain + '/login/token.php?username=' \
        + user + '&password=' + passwd + '&service=' + service
    req = urllib_req.Request(url_token)
    resp = urllib_req.urlopen(req).read()

    # JSON :)

    data = json.loads(resp.decode('utf8'))
    token = data.get('token')

    # Error, password / username wrong?

    if token is None:
        print(data.get('error'))
        exit()
    return token


# Get the userid necessary to get user courses

def get_user_info(token):
    url_info = 'https://' + domain + webservice + '?wstoken=' + token \
        + '&wsfunction=core_webservice_get_site_info'
    req = urllib_req.Request(url_info)
    resp = urllib_req.urlopen(req).read()

    # Yes, is a XML

    root = et.fromstring(resp)
    name = root.find("SINGLE/KEY[@name='fullname']/VALUE")  # Name of the student
    user_id = root.find("SINGLE/KEY[@name='userid']/VALUE").text
    print("User ID: " + user_id + ", " + name.text)
    return user_id


# Just simply return a list of courses ids

def get_courses(token, userid):
	url_courses = 'https://' + domain + webservice + '?wstoken=' \
		+ token + '&wsfunction=core_enrol_get_users_courses&userid=' \
	    + userid
	req = urllib_req.Request(url_courses)
	resp = urllib_req.urlopen(req).read()

	root = et.fromstring(resp)
	courses = []
	courses_names = root.findall("MULTIPLE/SINGLE/KEY[@name='fullname']/VALUE")
	ids = root.findall("MULTIPLE/SINGLE/KEY[@name='id']/VALUE")  # This is a list

	for i in range(0, len(ids)):

		if i < len(courses_names):
			courses.append({"name":courses_names[i], "id":ids[i]})
		else:
			courses.append({"name":ids[i], "id":ids[i]})
    
	return courses


# Get the course contents (files urls)

def get_course_content(token, course_id):
    url_course = 'https://' + domain + webservice + '?wstoken=' + token \
        + '&wsfunction=core_course_get_contents&courseid=' + course_id
        
    req = urllib_req.Request(url_course)
    resp = urllib_req.urlopen(req).read()
    root = et.fromstring(resp)
    xml_modules = "MULTIPLE/SINGLE/KEY[@name='modules']/MULTIPLE/"
    xml_contents = "SINGLE/KEY[@name='contents']/MULTIPLE/SINGLE"
    file_contents =  root.findall(xml_modules+xml_contents )  
    files = []
    for file_content in file_contents:
        file_url = file_content.find("KEY[@name='fileurl']/VALUE").text
        file_name = file_content.find("KEY[@name='filename']/VALUE"
                ).text
        file_type = file_content.find("KEY[@name='type']/VALUE").text
        if file_type == 'file':
            moodle_file = {}
            moodle_file['file_name'] = file_name
            moodle_file['file_url'] = file_url
            files.append(moodle_file)

    return files



"""
Saves the files of your aula global courses in the folder of your machine directory specified on dirPath.
If not dirPath is specified a 'cursos' folder will be created in this script's parent directory.
"""
def save_files(token, course_id, files, dirPath=None):
    course_id = course_id.replace("/","_")
    course_len = len(course_id)

	#Check if operative system is Windows (In windows if path is too long the cmd wont recognize it.)
    if os.name == "nt" and course_len > 55: 
        course_len = 55

    if dirPath == None:
        path = os.path.join(os.getcwd(),"cursos",course_id[:course_len-1])
    else:
        if not os.path.isdir(dirPath):
            raise(Exception("The path given as argument is not a directory"))
        path = os.path.join(dirPath, course_id[:course_len-1])

    if not os.path.exists(path):
        os.makedirs(path)

    for moodle_file in files:
        url = (moodle_file['file_url'] + '&token=' + token)
        file = os.path.join(path, moodle_file["file_name"].replace("/","_"))
        print("\nDownloading file to: ", file)

        try:
            response = urllib_req.urlopen(url)
        except Exception as e: # Most probabily an URLError (Exception for python 2 and 3 compatibility) [Lazy fix]
            print("Couldn't download this file. \n%s"%(e))

        with open(file, "wb") as f:
            f.write(response.read())


"""
Download all the files of the student's courses 
"""
def main():
    parser = \
        argparse.ArgumentParser(description='Aula Global from  Command Line')

    parser.add_argument('-u', metavar='User (NIA)', action='store',
                        required=True)
    parser.add_argument('-p', metavar='Password', action='store',
                        required=True)
    parser.add_argument('-d', metavar='Path for Output Directory (optional)', action='store',
                        required=False)
    args = parser.parse_args()


    token = get_token(args.u, args.p)
    userid = get_user_info(token)
    courses = get_courses(token, userid)
    for course_id in courses:
        print('Course: ' + course_id["name"].text)
        files_url = get_course_content(token, course_id["id"].text)
        if args.d:
        	save_files(token, course_id["name"].text, files_url, args.d)
        else:
        	save_files(token, course_id["name"].text, files_url)


if __name__ == '__main__':
    main()

