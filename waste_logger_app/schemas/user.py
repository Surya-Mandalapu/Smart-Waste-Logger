from pydantic import BaseModel, EmailStr, constr

class UserCreate(BaseModel):
    username: constr(strip_whitespace=True, min_length=3, max_length=20)
    email: EmailStr
    password: constr(min_length=8)
