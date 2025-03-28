

from app.repository.base_repository import BaseRepository
from app.schemas.users import UserCreateInternal, ProfileUpdate
from typing import List

class UserRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db)
        self.db = db

    async def get_all_users(self):
        query = "SELECT * FROM users;"
        print(query)
        return await self.fetch_all(query)

    async def get_user_by_email(self, email: str):
        try:
            query = "SELECT * FROM users WHERE email = :email"
            return await self.fetch_one(query=query, values={"email": email})
        except Exception as e:
            return {"error": "An error occurred while fetching user by email" + str(e)}

    async def get_user_by_username(self, username: str):
        try:
            query = "SELECT * FROM users WHERE username = :username"
            return await self.fetch_one(query=query, values={"username": username})
        except Exception as e:
            return {"error": "An error occurred while fetching user by username" + str(e)}

    async def create_user_internal(self, user: UserCreateInternal):
        try:
            query = """
                INSERT INTO users (username, email, password, first_name, last_name) 
                VALUES (:username, :email, :password, :first_name, :last_name) 
                RETURNING username, email, first_name, last_name;
            """
            values = {
                "username": user.username,
                "email": user.email,
                "password": user.password,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
            return await self.fetch_one(query=query, values=values)
        except Exception as e:
            return {"error": "An error occurred while creating user" + str(e)}

    async def update_user_verification(self, email: str):
        try:
            query = """
                UPDATE users 
                SET is_verified = TRUE 
                WHERE email = :email 
                RETURNING username, email, first_name, last_name;
            """
            return await self.execute(query=query, values={"email": email})
        except Exception as e:
            return {"error": "An error occurred while updating user verification status" + str(e)}
    async def update_profile(
        self, 
        profile_data: ProfileUpdate, 
        profile_picture_url: str, 
        additional_pictures_urls: List[str]):
        try:
            print("ssssss",profile_data)
            print("ssssss",profile_data.interests)
            query = """
                UPDATE users  SET 
                    gender = :gender,
                    sexual_preferences = :sexual_preferences,
                    bio = :bio,
                    pictures = :pictures,
                    interests = :interests,
                    updated_at = CURRENT_TIMESTAMP
                WHERE email = :email
                RETURNING username, email, first_name, last_name, gender, sexual_preferences, bio, interests, pictures;
            """
        
            values = {
                "gender": profile_data.gender,
                "sexual_preferences": profile_data.sexual_preferences,
                "bio": profile_data.bio,
                "interests": [profile_data.interests],
                "pictures": [profile_picture_url] + additional_pictures_urls,
                "email": profile_data.email
            }
        
            return await self.execute(query=query, values=values)
        except Exception as e:
            print(e)
            return {"error": "An error occurred while updating profile" + str(e)}
    async def close_session(self):
        await self.db.disconnect()