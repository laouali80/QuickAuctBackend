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

creation
{
"first_name": "test",
"last_name": "test",
"username": "test1",
"email": "test@gmail.com",
"password": "test"
}

A JSON Web Token authentication plugin for the Django REST Framework.
https://django-rest-framework-simplejwt.readthedocs.io/en/latest/

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

to generate a JWT_SECRETE_KEY

> > > openssl rand -hex 32
> > > 6f476259e482ea14fa88e35faa2d2504c3727f87442517fb1de5440520fa29e2

Redis setup
https://www.youtube.com/watch?v=DLKzd3bvgt8

1. Check if Redis is Already Running
   Run the following command in Command Prompt (cmd):
   netstat -ano | findstr :6379

   from dotenv import load_dotenv
   load_dotenv() # Load before using any os.getenv()

{"email":"laoualibachir2000@gmail.com","first_name":"LBID"}

email sending with template
https://www.youtube.com/watch?v=k5aPGb3px-U

{
"first_name": "test3",
"last_name": "test3",
"username": "test3",
"email": "test3@gmail.com",
"phone_number": "01232",
"password": "test1234",
"aggrement": true
}

vercel
https://youtu.be/_JoaelVNAWk?si=TBgAZqFP4usQda_e

supa base
https://youtu.be/IuY-xLNIJXw
vercel django and supabase realtime

Serializer errors checking
serializer = AuctionCreateSerializer(data=data, context={'user': user})

print(serializer.is_valid()) # This runs validation
print('Error while serializing: ', serializer.errors) # This shows actual validation error

campus clear out

what's It All About?
sell your pre-loved items (clothes, books, dorm/apartment gear, etc...)
Buy cool stuff at student-friendly Prices
Meet others and support a more sustainable campus
Graduating? This is a perfect chance to lighten the load before you leave - cash in and clear out!

All students, faculty, and staff are welcome!

email sending and receiving
https://forum.djangoproject.com/t/best-option-for-sending-receiving-email/33908
