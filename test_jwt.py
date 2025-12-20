from app.jwt import config

def check():
  data = config.decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTJmZGNmOTcyYzg3ZTUxMjMyNTZlYzAiLCJ0eXBlIjoicmVmcmVzaCIsImlhdCI6MTc2NjI0MTczMCwiZXhwIjoxNzY2ODQ2NTMwLCJpc3MiOiJzcGFyay1hcGkifQ.0JQ0FeHI08wtIe_Ohr4U8KMPeTK_NIrlwOfvMduS9fg")
  print("data", data)

check()
