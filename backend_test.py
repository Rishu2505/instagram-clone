#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Instagram-like App
Tests all endpoints with realistic data and scenarios
"""

import requests
import json
import base64
from datetime import datetime
import time

# Configuration
BASE_URL = "https://phototron-4.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

# Test data
TEST_USERS = [
    {
        "email": "alice.johnson@example.com",
        "password": "SecurePass123!",
        "username": "alice_j",
        "full_name": "Alice Johnson"
    },
    {
        "email": "bob.smith@example.com", 
        "password": "MyPassword456!",
        "username": "bob_smith",
        "full_name": "Bob Smith"
    },
    {
        "email": "carol.davis@example.com",
        "password": "StrongPass789!",
        "username": "carol_d",
        "full_name": "Carol Davis"
    }
]

# Sample base64 image (small 1x1 pixel PNG)
SAMPLE_IMAGE_B64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

class APITester:
    def __init__(self):
        self.tokens = {}
        self.user_ids = {}
        self.post_ids = []
        self.comment_ids = []
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "success": success,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def make_request(self, method, endpoint, data=None, token=None):
        """Make HTTP request with proper headers"""
        url = f"{BASE_URL}{endpoint}"
        headers = HEADERS.copy()
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def test_user_registration(self):
        """Test user registration with valid and invalid data"""
        print("\n=== Testing User Registration ===")
        
        # Test valid registration for all users
        for i, user_data in enumerate(TEST_USERS):
            response = self.make_request("POST", "/register", user_data)
            
            if response and response.status_code == 200:
                data = response.json()
                self.tokens[user_data["username"]] = data["access_token"]
                self.user_ids[user_data["username"]] = data["user"]["id"]
                self.log_result(f"Register user {user_data['username']}", True, 
                              f"User ID: {data['user']['id']}")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result(f"Register user {user_data['username']}", False, error_msg)
        
        # Test duplicate email
        response = self.make_request("POST", "/register", TEST_USERS[0])
        if response and response.status_code == 400:
            self.log_result("Register duplicate email", True, "Correctly rejected duplicate email")
        else:
            self.log_result("Register duplicate email", False, "Should reject duplicate email")
        
        # Test duplicate username
        duplicate_username = {
            "email": "new@example.com",
            "password": "Password123!",
            "username": TEST_USERS[0]["username"],
            "full_name": "New User"
        }
        response = self.make_request("POST", "/register", duplicate_username)
        if response and response.status_code == 400:
            self.log_result("Register duplicate username", True, "Correctly rejected duplicate username")
        else:
            self.log_result("Register duplicate username", False, "Should reject duplicate username")
    
    def test_user_login(self):
        """Test user login with valid and invalid credentials"""
        print("\n=== Testing User Login ===")
        
        # Test valid login
        login_data = {
            "email": TEST_USERS[0]["email"],
            "password": TEST_USERS[0]["password"]
        }
        response = self.make_request("POST", "/login", login_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Login with valid credentials", True, f"Token received")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("Login with valid credentials", False, error_msg)
        
        # Test invalid password
        invalid_login = {
            "email": TEST_USERS[0]["email"],
            "password": "wrongpassword"
        }
        response = self.make_request("POST", "/login", invalid_login)
        if response and response.status_code == 401:
            self.log_result("Login with invalid password", True, "Correctly rejected invalid password")
        else:
            self.log_result("Login with invalid password", False, "Should reject invalid password")
        
        # Test invalid email
        invalid_email = {
            "email": "nonexistent@example.com",
            "password": TEST_USERS[0]["password"]
        }
        response = self.make_request("POST", "/login", invalid_email)
        if response and response.status_code == 401:
            self.log_result("Login with invalid email", True, "Correctly rejected invalid email")
        else:
            self.log_result("Login with invalid email", False, "Should reject invalid email")
    
    def test_get_current_user(self):
        """Test getting current user profile"""
        print("\n=== Testing Get Current User ===")
        
        # Test with valid token
        token = self.tokens.get("alice_j")
        if token:
            response = self.make_request("GET", "/me", token=token)
            if response and response.status_code == 200:
                data = response.json()
                expected_fields = ["id", "email", "username", "full_name", "followers_count", "following_count", "posts_count"]
                if all(field in data for field in expected_fields):
                    self.log_result("Get current user with valid token", True, f"Username: {data['username']}")
                else:
                    self.log_result("Get current user with valid token", False, "Missing required fields")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Get current user with valid token", False, error_msg)
        else:
            self.log_result("Get current user with valid token", False, "No token available")
        
        # Test with invalid token
        response = self.make_request("GET", "/me", token="invalid_token")
        if response and response.status_code == 401:
            self.log_result("Get current user with invalid token", True, "Correctly rejected invalid token")
        else:
            self.log_result("Get current user with invalid token", False, "Should reject invalid token")
    
    def test_update_profile(self):
        """Test updating user profile"""
        print("\n=== Testing Update Profile ===")
        
        token = self.tokens.get("alice_j")
        if token:
            update_data = {
                "full_name": "Alice Johnson Updated",
                "bio": "Photography enthusiast and travel lover",
                "profile_pic": SAMPLE_IMAGE_B64
            }
            
            response = self.make_request("PUT", "/me", update_data, token=token)
            if response and response.status_code == 200:
                data = response.json()
                if data.get("full_name") == update_data["full_name"] and data.get("bio") == update_data["bio"]:
                    self.log_result("Update profile", True, "Profile updated successfully")
                else:
                    self.log_result("Update profile", False, "Profile data not updated correctly")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Update profile", False, error_msg)
        else:
            self.log_result("Update profile", False, "No token available")
    
    def test_get_user_profile(self):
        """Test getting other user's profile"""
        print("\n=== Testing Get User Profile ===")
        
        token = self.tokens.get("alice_j")
        user_id = self.user_ids.get("bob_smith")
        
        if token and user_id:
            response = self.make_request("GET", f"/users/{user_id}", token=token)
            if response and response.status_code == 200:
                data = response.json()
                if data.get("username") == "bob_smith":
                    self.log_result("Get other user profile", True, f"Retrieved profile for {data['username']}")
                else:
                    self.log_result("Get other user profile", False, "Wrong user data returned")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Get other user profile", False, error_msg)
        else:
            self.log_result("Get other user profile", False, "Missing token or user ID")
    
    def test_user_search(self):
        """Test user search functionality"""
        print("\n=== Testing User Search ===")
        
        token = self.tokens.get("alice_j")
        if token:
            # Search by username
            response = self.make_request("GET", "/users/search/bob", token=token)
            if response and response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    found_bob = any(user.get("username") == "bob_smith" for user in data)
                    if found_bob:
                        self.log_result("Search users by username", True, f"Found {len(data)} users")
                    else:
                        self.log_result("Search users by username", False, "Expected user not found")
                else:
                    self.log_result("Search users by username", False, "No users returned")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Search users by username", False, error_msg)
            
            # Search by full name
            response = self.make_request("GET", "/users/search/Carol", token=token)
            if response and response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    found_carol = any("Carol" in user.get("full_name", "") for user in data)
                    if found_carol:
                        self.log_result("Search users by full name", True, f"Found users with 'Carol'")
                    else:
                        self.log_result("Search users by full name", False, "Expected user not found")
                else:
                    self.log_result("Search users by full name", False, "Invalid response format")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Search users by full name", False, error_msg)
        else:
            self.log_result("Search users", False, "No token available")
    
    def test_follow_unfollow(self):
        """Test follow and unfollow functionality"""
        print("\n=== Testing Follow/Unfollow ===")
        
        alice_token = self.tokens.get("alice_j")
        bob_id = self.user_ids.get("bob_smith")
        carol_id = self.user_ids.get("carol_d")
        
        if alice_token and bob_id:
            # Test follow user
            response = self.make_request("POST", f"/users/{bob_id}/follow", token=alice_token)
            if response and response.status_code == 200:
                self.log_result("Follow user", True, "Successfully followed user")
                
                # Verify following status
                response = self.make_request("GET", f"/users/{bob_id}", token=alice_token)
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("is_following"):
                        self.log_result("Verify follow status", True, "Following status correctly updated")
                    else:
                        self.log_result("Verify follow status", False, "Following status not updated")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Follow user", False, error_msg)
            
            # Test follow already followed user
            response = self.make_request("POST", f"/users/{bob_id}/follow", token=alice_token)
            if response and response.status_code == 400:
                self.log_result("Follow already followed user", True, "Correctly rejected duplicate follow")
            else:
                self.log_result("Follow already followed user", False, "Should reject duplicate follow")
            
            # Test unfollow user
            response = self.make_request("DELETE", f"/users/{bob_id}/follow", token=alice_token)
            if response and response.status_code == 200:
                self.log_result("Unfollow user", True, "Successfully unfollowed user")
                
                # Verify unfollowing status
                response = self.make_request("GET", f"/users/{bob_id}", token=alice_token)
                if response and response.status_code == 200:
                    data = response.json()
                    if not data.get("is_following"):
                        self.log_result("Verify unfollow status", True, "Following status correctly updated")
                    else:
                        self.log_result("Verify unfollow status", False, "Following status not updated")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Unfollow user", False, error_msg)
        else:
            self.log_result("Follow/Unfollow tests", False, "Missing tokens or user IDs")
        
        # Test follow self (should fail)
        alice_id = self.user_ids.get("alice_j")
        if alice_token and alice_id:
            response = self.make_request("POST", f"/users/{alice_id}/follow", token=alice_token)
            if response and response.status_code == 400:
                self.log_result("Follow self", True, "Correctly rejected self-follow")
            else:
                self.log_result("Follow self", False, "Should reject self-follow")
    
    def test_create_posts(self):
        """Test post creation"""
        print("\n=== Testing Post Creation ===")
        
        # Create posts for different users
        for username in ["alice_j", "bob_smith"]:
            token = self.tokens.get(username)
            if token:
                post_data = {
                    "caption": f"Beautiful sunset photo by {username} 🌅 #photography #nature",
                    "media": [
                        {
                            "uri": SAMPLE_IMAGE_B64,
                            "type": "image"
                        }
                    ]
                }
                
                response = self.make_request("POST", "/posts", post_data, token=token)
                if response and response.status_code == 200:
                    data = response.json()
                    self.post_ids.append(data["id"])
                    self.log_result(f"Create post for {username}", True, f"Post ID: {data['id']}")
                else:
                    error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                    self.log_result(f"Create post for {username}", False, error_msg)
        
        # Test post with multiple media
        token = self.tokens.get("alice_j")
        if token:
            multi_media_post = {
                "caption": "Multiple photos from my trip! 📸",
                "media": [
                    {"uri": SAMPLE_IMAGE_B64, "type": "image"},
                    {"uri": SAMPLE_IMAGE_B64, "type": "image"}
                ]
            }
            
            response = self.make_request("POST", "/posts", multi_media_post, token=token)
            if response and response.status_code == 200:
                data = response.json()
                self.post_ids.append(data["id"])
                if len(data["media"]) == 2:
                    self.log_result("Create post with multiple media", True, f"Post with {len(data['media'])} media items")
                else:
                    self.log_result("Create post with multiple media", False, "Media count mismatch")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Create post with multiple media", False, error_msg)
    
    def test_get_posts(self):
        """Test getting individual posts"""
        print("\n=== Testing Get Posts ===")
        
        token = self.tokens.get("alice_j")
        if token and self.post_ids:
            post_id = self.post_ids[0]
            response = self.make_request("GET", f"/posts/{post_id}", token=token)
            
            if response and response.status_code == 200:
                data = response.json()
                required_fields = ["id", "user_id", "username", "caption", "media", "likes_count", "comments_count"]
                if all(field in data for field in required_fields):
                    self.log_result("Get single post", True, f"Retrieved post by {data['username']}")
                else:
                    self.log_result("Get single post", False, "Missing required fields")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Get single post", False, error_msg)
        else:
            self.log_result("Get single post", False, "No token or post IDs available")
    
    def test_feed(self):
        """Test feed functionality"""
        print("\n=== Testing Feed ===")
        
        # First, make alice follow bob to see bob's posts in feed
        alice_token = self.tokens.get("alice_j")
        bob_id = self.user_ids.get("bob_smith")
        
        if alice_token and bob_id:
            # Follow bob
            self.make_request("POST", f"/users/{bob_id}/follow", token=alice_token)
            
            # Get feed
            response = self.make_request("GET", "/feed", token=alice_token)
            if response and response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # Should contain posts from alice and bob
                    usernames = [post.get("username") for post in data]
                    has_own_posts = "alice_j" in usernames
                    has_followed_posts = "bob_smith" in usernames
                    
                    if has_own_posts and has_followed_posts:
                        self.log_result("Get feed", True, f"Feed contains {len(data)} posts from followed users and self")
                    elif has_own_posts:
                        self.log_result("Get feed", True, f"Feed contains own posts ({len(data)} posts)")
                    else:
                        self.log_result("Get feed", False, "Feed missing expected posts")
                else:
                    self.log_result("Get feed", False, "Invalid response format")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Get feed", False, error_msg)
        else:
            self.log_result("Get feed", False, "Missing tokens or user IDs")
    
    def test_user_posts(self):
        """Test getting user's posts"""
        print("\n=== Testing User Posts ===")
        
        token = self.tokens.get("alice_j")
        user_id = self.user_ids.get("bob_smith")
        
        if token and user_id:
            response = self.make_request("GET", f"/users/{user_id}/posts", token=token)
            if response and response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    # All posts should be from bob_smith
                    all_from_user = all(post.get("username") == "bob_smith" for post in data)
                    if all_from_user:
                        self.log_result("Get user posts", True, f"Retrieved {len(data)} posts from user")
                    else:
                        self.log_result("Get user posts", False, "Posts from wrong user")
                else:
                    self.log_result("Get user posts", False, "Invalid response format")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Get user posts", False, error_msg)
        else:
            self.log_result("Get user posts", False, "Missing token or user ID")
    
    def test_like_unlike(self):
        """Test like and unlike functionality"""
        print("\n=== Testing Like/Unlike ===")
        
        token = self.tokens.get("alice_j")
        if token and self.post_ids:
            post_id = self.post_ids[0]
            
            # Test like post
            response = self.make_request("POST", f"/posts/{post_id}/like", token=token)
            if response and response.status_code == 200:
                self.log_result("Like post", True, "Successfully liked post")
                
                # Verify like status
                response = self.make_request("GET", f"/posts/{post_id}", token=token)
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("is_liked") and data.get("likes_count") > 0:
                        self.log_result("Verify like status", True, f"Likes count: {data['likes_count']}")
                    else:
                        self.log_result("Verify like status", False, "Like status not updated")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Like post", False, error_msg)
            
            # Test like already liked post
            response = self.make_request("POST", f"/posts/{post_id}/like", token=token)
            if response and response.status_code == 400:
                self.log_result("Like already liked post", True, "Correctly rejected duplicate like")
            else:
                self.log_result("Like already liked post", False, "Should reject duplicate like")
            
            # Test unlike post
            response = self.make_request("DELETE", f"/posts/{post_id}/like", token=token)
            if response and response.status_code == 200:
                self.log_result("Unlike post", True, "Successfully unliked post")
                
                # Verify unlike status
                response = self.make_request("GET", f"/posts/{post_id}", token=token)
                if response and response.status_code == 200:
                    data = response.json()
                    if not data.get("is_liked"):
                        self.log_result("Verify unlike status", True, f"Likes count: {data['likes_count']}")
                    else:
                        self.log_result("Verify unlike status", False, "Unlike status not updated")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Unlike post", False, error_msg)
        else:
            self.log_result("Like/Unlike tests", False, "Missing token or post IDs")
    
    def test_comments(self):
        """Test comment functionality"""
        print("\n=== Testing Comments ===")
        
        token = self.tokens.get("alice_j")
        if token and self.post_ids:
            post_id = self.post_ids[0]
            
            # Test create comment
            comment_data = {"text": "Amazing photo! Love the colors 😍"}
            response = self.make_request("POST", f"/posts/{post_id}/comments", comment_data, token=token)
            
            if response and response.status_code == 200:
                data = response.json()
                self.comment_ids.append(data["id"])
                self.log_result("Create comment", True, f"Comment ID: {data['id']}")
                
                # Test get comments
                response = self.make_request("GET", f"/posts/{post_id}/comments", token=token)
                if response and response.status_code == 200:
                    comments = response.json()
                    if isinstance(comments, list) and len(comments) > 0:
                        comment_found = any(c.get("text") == comment_data["text"] for c in comments)
                        if comment_found:
                            self.log_result("Get comments", True, f"Retrieved {len(comments)} comments")
                        else:
                            self.log_result("Get comments", False, "Created comment not found")
                    else:
                        self.log_result("Get comments", False, "No comments returned")
                else:
                    error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                    self.log_result("Get comments", False, error_msg)
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Create comment", False, error_msg)
        else:
            self.log_result("Comment tests", False, "Missing token or post IDs")
    
    def test_delete_operations(self):
        """Test delete operations with authorization"""
        print("\n=== Testing Delete Operations ===")
        
        alice_token = self.tokens.get("alice_j")
        bob_token = self.tokens.get("bob_smith")
        
        # Test delete own comment
        if alice_token and self.comment_ids:
            comment_id = self.comment_ids[0]
            response = self.make_request("DELETE", f"/comments/{comment_id}", token=alice_token)
            if response and response.status_code == 200:
                self.log_result("Delete own comment", True, "Successfully deleted comment")
            else:
                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                self.log_result("Delete own comment", False, error_msg)
        
        # Test delete own post
        if alice_token and self.post_ids:
            # Find alice's post
            alice_post_id = None
            for post_id in self.post_ids:
                response = self.make_request("GET", f"/posts/{post_id}", token=alice_token)
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("username") == "alice_j":
                        alice_post_id = post_id
                        break
            
            if alice_post_id:
                response = self.make_request("DELETE", f"/posts/{alice_post_id}", token=alice_token)
                if response and response.status_code == 200:
                    self.log_result("Delete own post", True, "Successfully deleted post")
                    
                    # Verify post is deleted
                    response = self.make_request("GET", f"/posts/{alice_post_id}", token=alice_token)
                    if response and response.status_code == 404:
                        self.log_result("Verify post deletion", True, "Post no longer accessible")
                    else:
                        self.log_result("Verify post deletion", False, "Post still accessible")
                else:
                    error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                    self.log_result("Delete own post", False, error_msg)
        
        # Test unauthorized delete (bob trying to delete alice's remaining posts)
        if bob_token and self.post_ids:
            # Find alice's remaining post
            alice_post_id = None
            for post_id in self.post_ids:
                response = self.make_request("GET", f"/posts/{post_id}", token=alice_token)
                if response and response.status_code == 200:
                    data = response.json()
                    if data.get("username") == "alice_j":
                        alice_post_id = post_id
                        break
            
            if alice_post_id:
                response = self.make_request("DELETE", f"/posts/{alice_post_id}", token=bob_token)
                if response and response.status_code == 403:
                    self.log_result("Unauthorized post deletion", True, "Correctly rejected unauthorized deletion")
                else:
                    self.log_result("Unauthorized post deletion", False, "Should reject unauthorized deletion")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Instagram-like App Backend API Tests")
        print(f"Testing against: {BASE_URL}")
        print("=" * 60)
        
        # Run tests in order
        self.test_user_registration()
        self.test_user_login()
        self.test_get_current_user()
        self.test_update_profile()
        self.test_get_user_profile()
        self.test_user_search()
        self.test_follow_unfollow()
        self.test_create_posts()
        self.test_get_posts()
        self.test_feed()
        self.test_user_posts()
        self.test_like_unlike()
        self.test_comments()
        self.test_delete_operations()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        
        if failed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()