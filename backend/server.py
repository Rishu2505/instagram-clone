from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from bson import ObjectId


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    profile_pic: Optional[str] = None
    bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_following: bool = False

class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    profile_pic: Optional[str] = None
    bio: Optional[str] = None

class MediaItem(BaseModel):
    uri: str  # base64 encoded
    type: str  # 'image' or 'video'

class PostCreate(BaseModel):
    caption: Optional[str] = None
    media: List[MediaItem]

class CommentCreate(BaseModel):
    text: str

class Comment(BaseModel):
    id: str
    user_id: str
    username: str
    profile_pic: Optional[str] = None
    text: str
    created_at: datetime

class Post(BaseModel):
    id: str
    user_id: str
    username: str
    profile_pic: Optional[str] = None
    caption: Optional[str] = None
    media: List[MediaItem]
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    created_at: datetime

# Auth endpoints
@api_router.post("/register")
async def register(user_data: UserRegister):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create new user
    user_dict = {
        "email": user_data.email,
        "username": user_data.username,
        "full_name": user_data.full_name,
        "password_hash": hash_password(user_data.password),
        "profile_pic": None,
        "bio": None,
        "followers": [],
        "following": [],
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)
    
    # Create access token
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name
        }
    }

@api_router.post("/login")
async def login(user_data: UserLogin):
    # Find user
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user["email"],
            "username": user["username"],
            "full_name": user.get("full_name")
        }
    }

@api_router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    # Count followers and following
    followers_count = len(current_user.get("followers", []))
    following_count = len(current_user.get("following", []))
    
    # Count posts
    posts_count = await db.posts.count_documents({"user_id": user_id})
    
    return UserProfile(
        id=user_id,
        email=current_user["email"],
        username=current_user["username"],
        full_name=current_user.get("full_name"),
        profile_pic=current_user.get("profile_pic"),
        bio=current_user.get("bio"),
        followers_count=followers_count,
        following_count=following_count,
        posts_count=posts_count,
        is_following=False
    )

@api_router.put("/me", response_model=UserProfile)
async def update_profile(update_data: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    # Check if username is being changed and if it's already taken
    if update_data.username and update_data.username != current_user["username"]:
        existing = await db.users.find_one({"username": update_data.username})
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    # Update user
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    if update_dict:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
    
    # Get updated user
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    followers_count = len(updated_user.get("followers", []))
    following_count = len(updated_user.get("following", []))
    posts_count = await db.posts.count_documents({"user_id": user_id})
    
    return UserProfile(
        id=user_id,
        email=updated_user["email"],
        username=updated_user["username"],
        full_name=updated_user.get("full_name"),
        profile_pic=updated_user.get("profile_pic"),
        bio=updated_user.get("bio"),
        followers_count=followers_count,
        following_count=following_count,
        posts_count=posts_count,
        is_following=False
    )

# User endpoints
@api_router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_user_id = str(current_user["_id"])
    is_following = user_id in current_user.get("following", [])
    
    followers_count = len(user.get("followers", []))
    following_count = len(user.get("following", []))
    posts_count = await db.posts.count_documents({"user_id": user_id})
    
    return UserProfile(
        id=user_id,
        email=user["email"],
        username=user["username"],
        full_name=user.get("full_name"),
        profile_pic=user.get("profile_pic"),
        bio=user.get("bio"),
        followers_count=followers_count,
        following_count=following_count,
        posts_count=posts_count,
        is_following=is_following
    )

@api_router.get("/users/search/{query}")
async def search_users(query: str, current_user: dict = Depends(get_current_user)):
    users = await db.users.find({
        "$or": [
            {"username": {"$regex": query, "$options": "i"}},
            {"full_name": {"$regex": query, "$options": "i"}}
        ]
    }).limit(20).to_list(20)
    
    current_user_id = str(current_user["_id"])
    
    result = []
    for user in users:
        user_id = str(user["_id"])
        if user_id != current_user_id:
            result.append({
                "id": user_id,
                "username": user["username"],
                "full_name": user.get("full_name"),
                "profile_pic": user.get("profile_pic"),
                "is_following": user_id in current_user.get("following", [])
            })
    
    return result

@api_router.post("/users/{user_id}/follow")
async def follow_user(user_id: str, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    
    if current_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check if user exists
    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    if user_id in current_user.get("following", []):
        raise HTTPException(status_code=400, detail="Already following this user")
    
    # Add to following list
    await db.users.update_one(
        {"_id": ObjectId(current_user_id)},
        {"$addToSet": {"following": user_id}}
    )
    
    # Add to followers list
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"followers": current_user_id}}
    )
    
    return {"message": "Successfully followed user"}

@api_router.delete("/users/{user_id}/follow")
async def unfollow_user(user_id: str, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    
    # Remove from following list
    await db.users.update_one(
        {"_id": ObjectId(current_user_id)},
        {"$pull": {"following": user_id}}
    )
    
    # Remove from followers list
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"followers": current_user_id}}
    )
    
    return {"message": "Successfully unfollowed user"}

# Post endpoints
@api_router.post("/posts", response_model=Post)
async def create_post(post_data: PostCreate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    post_dict = {
        "user_id": user_id,
        "caption": post_data.caption,
        "media": [item.dict() for item in post_data.media],
        "likes": [],
        "created_at": datetime.utcnow()
    }
    
    result = await db.posts.insert_one(post_dict)
    post_id = str(result.inserted_id)
    
    # Get comments count
    comments_count = await db.comments.count_documents({"post_id": post_id})
    
    return Post(
        id=post_id,
        user_id=user_id,
        username=current_user["username"],
        profile_pic=current_user.get("profile_pic"),
        caption=post_data.caption,
        media=post_data.media,
        likes_count=0,
        comments_count=comments_count,
        is_liked=False,
        created_at=post_dict["created_at"]
    )

@api_router.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str, current_user: dict = Depends(get_current_user)):
    post = await db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get user info
    user = await db.users.find_one({"_id": ObjectId(post["user_id"])})
    
    current_user_id = str(current_user["_id"])
    is_liked = current_user_id in post.get("likes", [])
    
    # Get comments count
    comments_count = await db.comments.count_documents({"post_id": post_id})
    
    return Post(
        id=post_id,
        user_id=post["user_id"],
        username=user["username"] if user else "Unknown",
        profile_pic=user.get("profile_pic") if user else None,
        caption=post.get("caption"),
        media=[MediaItem(**item) for item in post["media"]],
        likes_count=len(post.get("likes", [])),
        comments_count=comments_count,
        is_liked=is_liked,
        created_at=post["created_at"]
    )

@api_router.get("/feed", response_model=List[Post])
async def get_feed(skip: int = 0, limit: int = 20, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    following = current_user.get("following", [])
    
    # Include own posts in feed
    user_ids = following + [current_user_id]
    
    # Get posts from followed users
    posts = await db.posts.find(
        {"user_id": {"$in": user_ids}}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for post in posts:
        # Get user info
        user = await db.users.find_one({"_id": ObjectId(post["user_id"])})
        
        post_id = str(post["_id"])
        is_liked = current_user_id in post.get("likes", [])
        
        # Get comments count
        comments_count = await db.comments.count_documents({"post_id": post_id})
        
        result.append(Post(
            id=post_id,
            user_id=post["user_id"],
            username=user["username"] if user else "Unknown",
            profile_pic=user.get("profile_pic") if user else None,
            caption=post.get("caption"),
            media=[MediaItem(**item) for item in post["media"]],
            likes_count=len(post.get("likes", [])),
            comments_count=comments_count,
            is_liked=is_liked,
            created_at=post["created_at"]
        ))
    
    return result

@api_router.get("/users/{user_id}/posts", response_model=List[Post])
async def get_user_posts(user_id: str, skip: int = 0, limit: int = 20, current_user: dict = Depends(get_current_user)):
    # Get posts from user
    posts = await db.posts.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Get user info
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    
    current_user_id = str(current_user["_id"])
    
    result = []
    for post in posts:
        post_id = str(post["_id"])
        is_liked = current_user_id in post.get("likes", [])
        
        # Get comments count
        comments_count = await db.comments.count_documents({"post_id": post_id})
        
        result.append(Post(
            id=post_id,
            user_id=post["user_id"],
            username=user["username"] if user else "Unknown",
            profile_pic=user.get("profile_pic") if user else None,
            caption=post.get("caption"),
            media=[MediaItem(**item) for item in post["media"]],
            likes_count=len(post.get("likes", [])),
            comments_count=comments_count,
            is_liked=is_liked,
            created_at=post["created_at"]
        ))
    
    return result

@api_router.delete("/posts/{post_id}")
async def delete_post(post_id: str, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    
    post = await db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post["user_id"] != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    await db.posts.delete_one({"_id": ObjectId(post_id)})
    await db.comments.delete_many({"post_id": post_id})
    
    return {"message": "Post deleted successfully"}

# Like endpoints
@api_router.post("/posts/{post_id}/like")
async def like_post(post_id: str, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    
    post = await db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if current_user_id in post.get("likes", []):
        raise HTTPException(status_code=400, detail="Already liked this post")
    
    await db.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$addToSet": {"likes": current_user_id}}
    )
    
    return {"message": "Post liked successfully"}

@api_router.delete("/posts/{post_id}/like")
async def unlike_post(post_id: str, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    
    await db.posts.update_one(
        {"_id": ObjectId(post_id)},
        {"$pull": {"likes": current_user_id}}
    )
    
    return {"message": "Post unliked successfully"}

# Comment endpoints
@api_router.post("/posts/{post_id}/comments", response_model=Comment)
async def create_comment(post_id: str, comment_data: CommentCreate, current_user: dict = Depends(get_current_user)):
    post = await db.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    user_id = str(current_user["_id"])
    
    comment_dict = {
        "post_id": post_id,
        "user_id": user_id,
        "text": comment_data.text,
        "created_at": datetime.utcnow()
    }
    
    result = await db.comments.insert_one(comment_dict)
    comment_id = str(result.inserted_id)
    
    return Comment(
        id=comment_id,
        user_id=user_id,
        username=current_user["username"],
        profile_pic=current_user.get("profile_pic"),
        text=comment_data.text,
        created_at=comment_dict["created_at"]
    )

@api_router.get("/posts/{post_id}/comments", response_model=List[Comment])
async def get_comments(post_id: str, skip: int = 0, limit: int = 50, current_user: dict = Depends(get_current_user)):
    comments = await db.comments.find(
        {"post_id": post_id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for comment in comments:
        user = await db.users.find_one({"_id": ObjectId(comment["user_id"])})
        
        result.append(Comment(
            id=str(comment["_id"]),
            user_id=comment["user_id"],
            username=user["username"] if user else "Unknown",
            profile_pic=user.get("profile_pic") if user else None,
            text=comment["text"],
            created_at=comment["created_at"]
        ))
    
    return result

@api_router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, current_user: dict = Depends(get_current_user)):
    current_user_id = str(current_user["_id"])
    
    comment = await db.comments.find_one({"_id": ObjectId(comment_id)})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment["user_id"] != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    await db.comments.delete_one({"_id": ObjectId(comment_id)})
    
    return {"message": "Comment deleted successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()