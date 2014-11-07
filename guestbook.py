import cgi
import os
import urllib
import time
import jinja2
import webapp2
import MySQLdb
import gzip

from google.appengine.api import users
from google.appengine.api import files
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'], 
    autoescape=True)

# Define your production Cloud SQL instance information.
_INSTANCE_NAME = 'achint-sfsu:blobdb512'


class DBConnector(): 

    def createConnection(self):

       # Display existing file and a form to add new entries.
        if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
            db = MySQLdb.connect(unix_socket='/cloudsql/' + _INSTANCE_NAME, db='sfsu', user='root')
        else:
            db = MySQLdb.connect(host='173.194.241.94', port=3306, db='sfsu', user='root')
            # Alternatively, connect to a Google Cloud SQL instance using:
            # db = MySQLdb.connect(host='173.194.241.94', port=3306, user='root') 
        
        return db        


class MainPage(webapp2.RequestHandler):

    def get(self):
        
        #define a default nickname of the user
        nickname        = "Guest" 
        
        dbhandle    = DBConnector()
        db          = dbhandle.createConnection()
        cursor      = db.cursor()
        
        
        category = self.request.get('category')


        if category:
            cursor.execute('SELECT fid, title, blob_id, filetype, upload_timestamp FROM uploads where filetype = %s order by fid desc', category)
        else:    
            cursor.execute('SELECT fid, title, blob_id, filetype, upload_timestamp FROM uploads order by fid desc')
            category = ""

        # Create a list of files to render with the HTML.
        uploaded_files = [];
        for row in cursor.fetchall():
          uploaded_files.append(dict([('fid',row[0]),
                                    ('title',row[1]),
                                    ('blob_id',row[2]),
                                    ('filetype',row[3]),
                                    ('timestamp',time.ctime(row[4]))
                                 ]))

        

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            user = users.get_current_user()
            nickname = user.nickname()
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'


        blob_upload_url = blobstore.create_upload_url("/upload")    

        template_values = {
            
            'url': url,
            'url_linktext': url_linktext,
            'user_nickname': nickname,
            'uploaded_files': uploaded_files,
            'upload_url': blob_upload_url,
            'category': category,
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))


class ImageDetailPage(webapp2.RequestHandler):

    def get(self):
        
        
        dbhandle    = DBConnector()
        db          = dbhandle.createConnection()
        cursor      = db.cursor()

        
        image_id = self.request.get('image_id')    
        cursor.execute('SELECT title, blob_id, filetype, upload_timestamp, fid FROM uploads where fid = %s', image_id)

        # Create a list of files to render with the HTML.
        uploaded_files = [];
        for row in cursor.fetchall():
          uploaded_files.append(dict([('title',row[0]),
                                 ('blob_id',row[1]),
                                 ('filetype',row[2]),
                                 ('timestamp',time.ctime(row[3]))
                                 ]))
          blob_id = row[1]
          
        

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            user = users.get_current_user()
            nickname = user.nickname()
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

        template_values = {
            
            'url': url,
            'url_linktext': url_linktext,
            'user_nickname': nickname,
            'uploaded_files': uploaded_files,
            'blob_id': blob_id,
            'image_id': image_id,
        }

        template = JINJA_ENVIRONMENT.get_template('imagedetail.html')
        self.response.write(template.render(template_values))




class UploadFile(blobstore_handlers.BlobstoreUploadHandler):

    def post(self):
        

        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        


        #collect the field values from the form
        timestamp   = int(str(time.time()).split('.')[0])
        filename    = self.request.get('file')
        title       = self.request.get('title')
        filetype    = int(self.request.get('filetype'))
        blobkey     = blob_info.key()

        dbhandle    = DBConnector()
        db          = dbhandle.createConnection()
        cursor      = db.cursor()

        # Note that the only format string supported is %s
        cursor.execute('INSERT INTO uploads (filetype, title, upload_timestamp, blob_id) VALUES (%s, %s, %s, %s)', (filetype, title, timestamp, blobkey))
        db.commit()
        db.close()


        #query_params = {'guestbook_name': "test_book"}
        #self.redirect('/?' + urllib.urlencode(query_params))
        self.redirect('/')

class ResizeFile(webapp2.RequestHandler):

    def post(self):
        
        #collect the field values from the form
        
        x           = float(self.request.get('x'))
        y           = float(self.request.get('y'))
        w           = float(self.request.get('w'))
        h           = float(self.request.get('h'))

        blob_id     = self.request.get('blob_id')

        blob_info   = blobstore.get(blob_id)
        
        if blob_info:

            img = images.Image(blob_key=blob_id)
            
                
            #chaudai = float(img.width)
            #unchai  = float(img.height)    

            #left_x = x/chaudai
            #top_y = y/unchai

            #right_x = (x+w)/chaudai
            #bottom_y = (y+h)/unchai
            
            img.crop(0.3, 0.3, 0.7, 0.7)
            #img.im_feeling_lucky()
            thumbnail = img.execute_transforms(output_encoding=images.JPEG)

            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(thumbnail)


class PlayImage(webapp2.RequestHandler):

    def get(self):
      
        play_action = self.request.get('play_action')
        
        dbhandle    = DBConnector()
        db          = dbhandle.createConnection()
        cursor      = db.cursor()

        
        image_id = self.request.get('image_id')    
        cursor.execute('SELECT title, blob_id, filetype, upload_timestamp, fid FROM uploads where fid = %s', image_id)

        db_image = cursor.fetchone()

        blob_id     = db_image[1]

        blob_info   = blobstore.get(blob_id)
        
        if blob_info:

            img = images.Image(blob_key=blob_id)
            
            if play_action == "flipH":
                img.horizontal_flip()
            elif play_action == "flipV":
                img.vertical_flip()
            elif play_action == "rotateR":
                img.rotate(90)
            elif play_action == "rotateL":
                img.rotate(270)

            img.resize(width=600)
            
            #img.im_feeling_lucky()
            thumbnail = img.execute_transforms(output_encoding=images.JPEG)

            self.response.headers['Content-Type'] = 'image/jpeg'
            self.response.out.write(thumbnail)


class Thumbnailer(webapp2.RequestHandler):
    def get(self):
        blob_key = self.request.get("blob_key")
        if blob_key:
            blob_info = blobstore.get(blob_key)

            if blob_info:
                img = images.Image(blob_key=blob_key)
                img.resize(width=200, height=150)
                #img.im_feeling_lucky()
                thumbnail = img.execute_transforms(output_encoding=images.JPEG)

                self.response.headers['Content-Type'] = 'image/jpeg'
                self.response.out.write(thumbnail)
                return

        # Either "blob_key" wasn't provided, or there was no value with that ID
        # in the Blobstore.
        self.error(404)
        #self.response.out('Image Not Found')

class LargeImage(webapp2.RequestHandler):
    def get(self):
        blob_key = self.request.get("blob_key")
        if blob_key:
            blob_info = blobstore.get(blob_key)

            if blob_info:
                img = images.Image(blob_key=blob_key)
                img.resize(width=600)
                #img.im_feeling_lucky()
                thumbnail = img.execute_transforms(output_encoding=images.JPEG)

                self.response.headers['Content-Type'] = 'image/jpeg'
                self.response.out.write(thumbnail)
                return

        # Either "blob_key" wasn't provided, or there was no value with that ID
        # in the Blobstore.
        self.error(404)
        #self.response.out('Image Not Found')


class GetRawFile(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self):
        blob_key = self.request.get("blob_key")
        if blob_key:
            blob_info = blobstore.get(blob_key)

            if blob_info:
                self.send_blob(blob_key)
                return

        # Either "blob_key" wasn't provided, or there was no value with that ID
        # in the Blobstore.
        self.error(404)
        #self.response.out('Image Not Found')


class GetZipFile(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self):
        blob_key = self.request.get("blob_key")
        if blob_key:
            blob_info = blobstore.get(blob_key)

            blobfile = files.blobstore.create(mime_type='application/gzip')
            with files.open(blobfile, 'a') as f:
                gz = gzip.GzipFile(fileobj=f,mode='wb')
                
                rowfile = GetRawFile()

                gz.write(rowfile.get(blob_key))
                gz.close()
                return

        # Either "blob_key" wasn't provided, or there was no value with that ID
        # in the Blobstore.
        self.error(404)
        #self.response.out('Image Not Found')





class DeleteFile(webapp2.RequestHandler):
    def get(self):
        blob_key = self.request.get("blob_key")
        if blob_key:
            blob_info = blobstore.get(blob_key)

            dbhandle    = DBConnector()
            db          = dbhandle.createConnection()
            cursor      = db.cursor()

            #delete from blobstore      
            blob_info.delete()

            #delete record from mySQL
            cursor.execute('DELETE FROM `uploads` where blob_id = %s', blob_key)
            db.commit()

            
        self.redirect('/')


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/upload', UploadFile),
    ('/thumb', Thumbnailer),
    ('/delete', DeleteFile),
    ('/getrawfile', GetRawFile),
    ('/imagelarge', LargeImage),
    ('/imagedetailpage', ImageDetailPage),
    ('/resizefile', ResizeFile),
    ('/playimage', PlayImage),
    ('/getzipfile', GetZipFile),
], debug=True)
