from flask import Flask, request, render_template, send_from_directory, jsonify
import os
import socket
from datetime import datetime
import qrcode
from io import BytesIO
import base64
import threading
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# 获取本机IP地址
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# 生成二维码
def generate_qr_code(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


@app.route('/')
def index():
    ip = get_local_ip()
    port = 5000
    upload_url = f"http://{ip}:{port}/upload-page"
    qr_code = generate_qr_code(upload_url)

    # 获取已上传的图片列表
    images = []
    if os.path.exists(UPLOAD_FOLDER):
        images = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        images.sort(reverse=True)  # 最新的在前面

    return render_template('index.html',
                           qr_code=qr_code,
                           upload_url=upload_url,
                           images=images)


@app.route('/upload-page')
def upload_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手机上传图片</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 20px; }
            .upload-btn { 
                background: #4CAF50; 
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 5px; 
                font-size: 16px; 
                margin: 20px;
                cursor: pointer;
            }
            #preview { max-width: 100%; margin: 20px 0; }
            .status { margin: 10px; color: #666; }
        </style>
    </head>
    <body>
        <h2>📱 上传图片到电脑</h2>

        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" accept="image/*" capture="camera" style="display: none;">
            <button type="button" class="upload-btn" onclick="document.getElementById('fileInput').click()">
                📸 选择或拍照上传
            </button>
        </form>

        <div id="preview"></div>
        <div id="status" class="status"></div>

        <script>
            document.getElementById('fileInput').addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (!file) return;

                // 预览图片
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('preview').innerHTML = 
                        `<img src="${e.target.result}" style="max-width: 300px; border: 2px solid #ddd; border-radius: 5px;">`;
                };
                reader.readAsDataURL(file);

                // 上传图片
                uploadFile(file);
            });

            function uploadFile(file) {
                const formData = new FormData();
                formData.append('image', file);

                document.getElementById('status').innerHTML = '⏳ 上传中...';
                document.querySelector('.upload-btn').disabled = true;

                fetch('/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('status').innerHTML = '✅ 上传成功！';
                        document.getElementById('status').style.color = 'green';
                        setTimeout(() => {
                            document.getElementById('status').innerHTML = '可以继续上传新图片';
                            document.getElementById('status').style.color = '#666';
                            document.querySelector('.upload-btn').disabled = false;
                            document.getElementById('preview').innerHTML = '';
                        }, 2000);
                    }
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = '❌ 上传失败';
                    document.getElementById('status').style.color = 'red';
                    document.querySelector('.upload-btn').disabled = false;
                });
            }
        </script>
    </body>
    </html>
    '''


@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'})

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': '没有选择文件'})

    if file:
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        return jsonify({'success': True, 'filename': filename})


@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/images')
def list_images():
    images = []
    if os.path.exists(UPLOAD_FOLDER):
        images = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        images.sort(reverse=True)
    return jsonify(images)


if __name__ == '__main__':
    ip = get_local_ip()
    print(f"🖥️  服务器启动在: http://{ip}:5000")
    print("📱 用手机扫描二维码即可上传图片")
    app.run(host='0.0.0.0', port=5000, debug=True)