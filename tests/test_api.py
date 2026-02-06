"""
Test suite for the Mergington High School Activities API endpoints.
"""

import pytest


class TestRootEndpoint:
    """Tests for the root endpoint."""
    
    def test_root_redirects_to_index(self, client):
        """Test that / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivitiesEndpoint:
    """Tests for the GET /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Should have all 9 activities
        assert len(data) == 9
        
        # Check that specific activities exist
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_response_structure(self, client):
        """Test that activity data has the correct structure."""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of one activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
    
    def test_get_activities_has_participants(self, client):
        """Test that activities contain participant data."""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have initial participants
        assert isinstance(data["Chess Club"]["participants"], list)
        assert len(data["Chess Club"]["participants"]) > 0


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_new_participant(self, client, reset_activities):
        """Test signing up a new participant for an activity."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_already_registered_student(self, client, reset_activities):
        """Test that signing up an already registered student returns error."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test that signing up for a non-existent activity returns 404."""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_multiple_participants(self, client, reset_activities):
        """Test signing up multiple different participants."""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                "/activities/Programming Class/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for email in emails:
            assert email in activities_data["Programming Class"]["participants"]
    
    def test_signup_email_parameter_encoding(self, client, reset_activities):
        """Test that email parameters are properly encoded."""
        email = "student+test@mergington.edu"
        response = client.post(
            "/activities/Art Studio/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Art Studio"]["participants"]


class TestActivityDataIntegrity:
    """Tests to verify activity data is maintained correctly."""
    
    def test_other_activities_unaffected_by_signup(self, client, reset_activities):
        """Test that signing up for one activity doesn't affect others."""
        # Get initial state of Basketball Team
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        basketball_initial = initial_data["Basketball Team"]["participants"].copy()
        
        # Sign up for a different activity
        client.post(
            "/activities/Tennis Club/signup",
            params={"email": "newplayer@mergington.edu"}
        )
        
        # Check Basketball Team wasn't affected
        final_response = client.get("/activities")
        final_data = final_response.json()
        assert final_data["Basketball Team"]["participants"] == basketball_initial
    
    def test_signup_response_contains_confirmation(self, client, reset_activities):
        """Test that signup response contains confirmation message."""
        email = "student@mergington.edu"
        response = client.post(
            "/activities/Drama Club/signup",
            params={"email": email}
        )
        data = response.json()
        assert email in data["message"]
        assert "Drama Club" in data["message"]


class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_signup_missing_email_parameter(self, client):
        """Test signup without email parameter."""
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422  # Validation error
    
    def test_signup_empty_email_parameter(self, client, reset_activities):
        """Test signup with empty email parameter."""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": ""}
        )
        # Empty string should still be processed by FastAPI
        # The API will accept but the email might not be useful
        # This behavior depends on the actual validation logic
        assert response.status_code in [200, 400]
    
    def test_get_activities_content_type(self, client):
        """Test that GET /activities returns JSON."""
        response = client.get("/activities")
        assert response.headers["content-type"].startswith("application/json")
    
    def test_signup_response_content_type(self, client, reset_activities):
        """Test that signup response is JSON."""
        response = client.post(
            "/activities/Robotics Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.headers["content-type"].startswith("application/json")


class TestActivityLimits:
    """Tests for activity capacity and limits."""
    
    def test_activity_capacity_info_present(self, client):
        """Test that max_participants is returned for each activity."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "max_participants" in activity_data
            assert isinstance(activity_data["max_participants"], int)
            assert activity_data["max_participants"] > 0
    
    def test_participant_count_not_exceeds_max(self, client, reset_activities):
        """Test that participant count doesn't exceed max_participants."""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            participant_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            assert participant_count <= max_participants
