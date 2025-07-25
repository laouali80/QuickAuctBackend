super
lbid
laouali1234

laouali
laouali1234

users
test
test1234

work
work12345

quickauct
quick1234

login
{
"email": "test@gmail.com",
"password": "test"
}

{
"email": "work@gmail.com",
"password": "work12345"
}

creation
{
"first_name": "test",
"last_name": "test",
"username": "test1",
"email": "test@gmail.com",
"password": "test"
}

{
"first_name": "test",
"last_name": "test",
"username": "test1",
"email": "test@gmail.com",
"phone_number": "07070707",
"password": "test1234",
"aggrement":true
}

create your own .env

SECRET_KEY = ''

ENVIRONMENT= DEVELOPMENT

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

JWT_SECRET_KEY = ''
JWT_ALGORITHM = "",
ACCESS_TOKEN_EXPIRE_MINUTES =
REFRESH_TOKEN_EXPIRE_TIME =

**_Resources_**

A JSON Web Token authentication plugin for the Django REST Framework.
https://django-rest-framework-simplejwt.readthedocs.io/en/latest/

Redis setup
https://www.youtube.com/watch?v=DLKzd3bvgt8

email sending with template
https://www.youtube.com/watch?v=k5aPGb3px-U

vercel
https://youtu.be/_JoaelVNAWk?si=TBgAZqFP4usQda_e

supa base
https://youtu.be/IuY-xLNIJXw
vercel django and supabase realtime

email sending and receiving
https://forum.djangoproject.com/t/best-option-for-sending-receiving-email/33908

**_Documentation_**
to generate a JWT_SECRETE_KEY

> > > openssl rand -hex 32
> > > 6f476259e482ea14fa88e35faa2d2504c3727f87442517fb1de5440520fa29e2

1. Check if Redis is Already Running
   Run the following command in Command Prompt (cmd):
   netstat -ano | findstr :6379

   from dotenv import load_dotenv
   load_dotenv() # Load before using any os.getenv()

{"email":"laoualibachir2000@gmail.com","first_name":"LBID"}

{
"first_name": "test3",
"last_name": "test3",
"username": "test3",
"email": "test3@gmail.com",
"phone_number": "01232",
"password": "test1234",
"aggrement": true
}

Serializer errors checking
serializer = AuctionCreateSerializer(data=data, context={'user': user})

print(serializer.is_valid()) # This runs validation
print('Error while serializing: ', serializer.errors) # This shows actual validation error

https://medium.com/@bhairabpatra.iitd/env-file-in-react-js-09d11dc77924

render server
https://www.youtube.com/watch?v=ZjVzHcXCeMU

{
"auction_id": 123,
"reason": "FRAUD",
"description": "Seller is using fake profile and asking for money outside the app."
}

aws del
https://www.youtube.com/watch?v=rgE6aZkSMlY

added ruff, black and autopep8 python extension

https://www.youtube.com/watch?v=GtheHlioTrA&list=PL5E1F5cTSTtRHN1WynTlFmr9ozlfZEUNI&index=3

aws s3
https://www.youtube.com/watch?v=-DU6Y-x-2MA

https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings

railway
https://www.youtube.com/watch?v=AjKhxWgGpjY

railway postgres debug
https://stackoverflow.com/questions/78777419/django-db-utils-operationalerror-could-not-translate-host-name-postgres-railwa
