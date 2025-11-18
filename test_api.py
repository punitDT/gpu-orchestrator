"""
Simple test script to verify the GPU Orchestrator API.
Run this after starting the server to test basic functionality.
"""
import asyncio
import httpx
import json


async def test_health():
    """Test health endpoint."""
    print("\n🔍 Testing /health endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    print("✅ Health check passed")


async def test_gpu_status():
    """Test GPU status endpoint."""
    print("\n🔍 Testing /gpu-status endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/gpu-status")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
    print("✅ GPU status check passed")


async def test_generate_logo():
    """Test logo generation endpoint."""
    print("\n🔍 Testing /generate-logo endpoint...")
    
    payload = {
        "prompt": "A modern minimalist logo for a tech startup",
        "width": 512,
        "height": 512,
        "num_inference_steps": 20,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8080/generate-logo",
            json=payload,
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
        
        if result.get("status") == "warming_up":
            print(f"⏳ GPU is warming up. ETA: {result['data']['eta_seconds']} seconds")
            print("💡 Try again in a moment once GPU is ready")
        elif result.get("status") == "success":
            print("✅ Logo generated successfully!")
            if "image_base64" in result.get("data", {}):
                print(f"📸 Image data length: {len(result['data']['image_base64'])} chars")
        
        assert response.status_code == 200


async def main():
    """Run all tests."""
    print("🧪 GPU Orchestrator API Tests")
    print("=" * 50)
    
    try:
        await test_health()
        await test_gpu_status()
        await test_generate_logo()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        
    except httpx.ConnectError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the server is running on http://localhost:8080")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

