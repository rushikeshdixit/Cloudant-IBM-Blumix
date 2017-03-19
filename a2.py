from flask import Flask, request, render_template, make_response
from cloudant.client import Cloudant
import hashlib
import os
import time

connection_json = {
    "username": "<username>",
    "password": "<password>",
    "host": "<host_key>",
    "port": 443,
    "url": "<blumix_URL>"
}

client = Cloudant(cloudant_user=connection_json["username"], auth_token=connection_json["password"],
                  url=connection_json["url"])
# Connect to the account
client.connect()

my_database = client["<container_name>"]
path = os.getcwd()
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('a2.html')


@app.route('/upload', methods=['POST'])
def upload():
    list_of_files = request.files.getlist('file')
    # list of files
    for f in list_of_files:
        f.save(path+f.filename)

    for f in list_of_files:
        with open(path+f.filename, 'rb') as check_file:
            buf = check_file.read()
            hasher = hashlib.md5()
            hasher.update(buf)
            hashed_val = hasher.hexdigest()
            data = {'file_name': f.filename, 'data': buf, 'hash': hashed_val,
                    'Last Modified': time.ctime(os.stat(path+f.filename).st_mtime),
                    'Version': 1}

            # if database already exists
            if (my_database):
                if (f.filename not in [doc['file_name'] for doc in my_database]):
                    my_database.create_document(data)
                    return '<h1>Upload successful</h1>'
                # implies that the file already exists
                else:
                    # get the highest version number
                    ver = max([doc['Version'] for doc in my_database if doc['file_name'] == f.filename])
                    # if the hash of the file matches that of any in the documents (i.e. same file)
                    if hashed_val in [doc['hash'] for doc in my_database]:
                        # do nothing
                        return '<h1>Upload unsuccessful!</h1>'

                    # same file name but diff. content (i.e. revision)
                    else:
                        data['Version'] = ver+1
                        my_database.create_document(data)
                        return '<h1>Upload successful!</h1>'

            # first time
            else:
                my_database.create_document(data)
                return '<h1>Upload Successful!</h1>'


@app.route('/list_files', methods=['POST'])
def list_file():
    # for f_all in my_database:
    #     print(f_all['file_name'],f_all['Version'], f_all['Last Modified'])
    # return '<h1>list of files</h1>'+'\n'.join(['<p>'+f_all['file_name']+'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    #                                            +f_all['Last Modified']+'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
    #                                            +str(f_all['Version'])+'</p>' for f_all in my_database])
    return render_template('table.html', my_database=my_database)

@app.route('/download', methods=['POST'])
def download_file():
    file_name = request.form.get('filename')
    version_num = request.form.get('version')
    response_file = [doc for doc in my_database if doc['Version']==int(version_num) and doc['file_name']==file_name]
    if response_file:
        response = make_response(response_file[0]['data'])
        response.headers["Content-Disposition"] = 'attachment; filename='+file_name
        response.headers["Cache-Control"] = "must-revalidate"
        response.headers["Pragma"] = "must-revalidate"
        response.headers["Content-type"] = "application/"+file_name.split('.')[1]
    else:
        return '<h1>File not found</h1>'
    return response


@app.route('/delete', methods=['POST'])
def delete():
    file_name = request.form['filename']
    version_num = request.form['version']
    for document in my_database:
        if document['file_name'] == file_name and document['Version'] == int(version_num):
            print("File found and deleted")
            document.delete()
            #document.delete_attachment(file_name)
        else:
            print ('File not found')
            return render_template('a2.html')

if __name__ == "__main__":
    app.run(debug=True)
    # Disconnect from the account
    client.disconnect()
