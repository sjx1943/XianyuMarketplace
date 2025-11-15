from motor import motor_tornado
import asyncio
import datetime

async def test_mongo_connection():
    # 連接到 MongoDB
    mongo = motor_tornado.MotorClient('mongodb://localhost:27017').chat_app
    try:
        # 嘗試進行一個簡單的操作來確認連接
        await mongo.command('ping')
        print("MongoDB 連接成功")
    except Exception as e:
        print(f"MongoDB 連接失敗: {e}")
        return

    # 準備要插入的測試數據
    test_data = {
        'sender_id': 5,
        'receiver_id': 2,
        'product_id': 1,
        'product_name': 'Test Product2111',
        'message': 'This is a tornadoAPP message',
        'status': 'unread',
        'timestamp': datetime.datetime.utcnow()
    }

    try:
        # 將測試數據插入到 chat_messages 集合中
        result = await mongo.chat_messages.insert_one(test_data)
        print(f"插入文檔成功，ID: {result.inserted_id}")
    except Exception as e:
        print(f"插入文檔失敗: {e}")

if __name__ == "__main__":
    asyncio.run(test_mongo_connection())