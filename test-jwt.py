from app.jwt.config import create_token, hash_password, verify_password,create_refresh_token,create_access_token,decode_token

# token = create_token({"sub": "user_id", "type": "access"}, 30)
# print(token)
# accessToken = create_access_token("user_id")
# print(accessToken)
# refreshToken = create_refresh_token("user_id")
# print(refreshToken)
# hashed_password = hash_password("password")
# print(hashed_password)
# is_valid = verify_password("passwoasrd", hashed_password)
# print(is_valid)
d = decode_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyX2lkIiwidHlwZSI6InJlZnJlc2giLCJpYXQiOjE3NjQ1NjMwOTAsImV4cCI6MTc2NTE2Nzg5MCwiaXNzIjoic3BhcmstYXBpIn0.0PD-xdQRjbhSgApTCl_NR8tSn3OfoJlb83TDWtazCgM")
print(d)