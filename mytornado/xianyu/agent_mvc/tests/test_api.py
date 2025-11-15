import pytest
import requests
import json
import time
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:8000"
TEST_USER = {
    "username": f"testuser_{int(time.time())}",
    "password": "password123",
    "email": f"test_{int(time.time())}@example.com"
}
session = requests.Session()

@pytest.fixture(scope="module")
def authenticated_session():
    """
    Handles XSRF, registers and logs in a new user, returns an authenticated session.
    """
    # 1. GET the register page to receive the _xsrf cookie and token
    reg_page_response = session.get(f"{BASE_URL}/register")
    assert reg_page_response.status_code == 200
    soup = BeautifulSoup(reg_page_response.text, 'html.parser')
    xsrf_token = soup.find('input', {'name': '_xsrf'})['value']

    # 2. Register the user, including the _xsrf token in the form data
    register_data = TEST_USER.copy()
    register_data['_xsrf'] = xsrf_token
    reg_response = session.post(f"{BASE_URL}/register", data=register_data, allow_redirects=True)
    # A successful registration redirects to the login page
    assert reg_response.status_code == 200
    assert "/login" in reg_response.url

    # 3. Login with the new user
    # We need a new XSRF token from the login page we were redirected to
    soup = BeautifulSoup(reg_response.text, 'html.parser')
    xsrf_token = soup.find('input', {'name': '_xsrf'})['value']
    
    login_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
        "_xsrf": xsrf_token
    }
    login_response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    
    # A successful login should redirect to the main page
    assert login_response.status_code == 200
    assert "/main" in login_response.url

    return session

def test_publish_product(authenticated_session):
    """测试发布商品API。"""
    # First, GET the upload page to get a valid XSRF token for this form
    upload_page_response = authenticated_session.get(f"{BASE_URL}/product/upload")
    assert upload_page_response.status_code == 200
    soup = BeautifulSoup(upload_page_response.text, 'html.parser')
    xsrf_token = soup.find('input', {'name': '_xsrf'})['value']

    product_data = {
        "name": "Test Product",
        "description": "This is a test product.",
        "price": "99.99",
        "quantity": "10",
        "tag": "electronics",
        "_xsrf": xsrf_token
    }
    files = {'images': ('test.jpg', b'file_content', 'image/jpeg')}
    
    response = authenticated_session.post(f"{BASE_URL}/product/upload", data=product_data, files=files)
    
    # A successful upload redirects to the product detail page
    assert response.status_code == 200 
    assert "product/detail" in response.url

def test_get_product_list(authenticated_session):
    """测试获取商品列表API。"""
    # This test depends on the previous test creating a product.
    response = authenticated_session.get(f"{BASE_URL}/product_list") # Corrected URL
    assert response.status_code == 200
    
    products = response.json()
    assert isinstance(products, list)
    
    # Verify that the product we just created exists in the list
    assert any(p['name'] == 'Test Product' for p in products)