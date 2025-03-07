#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - 2025 Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : app.py

import os
import random
import uuid
import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np
from pathlib import Path
import tempfile
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['PROCESSED_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processed')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB
app.secret_key = 'your_secret_key_here'  # 用于flash消息

# 确保上传和处理目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def add_scanner_effect(image):
    """添加扫描效果到图像"""
    # 转换为RGB确保图像模式兼容
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # 1. 轻微旋转（模拟纸张放置不正）
    rotation_angle = random.uniform(-0.5, 0.5)
    image = image.rotate(rotation_angle, resample=Image.BICUBIC, expand=False)

    # 2. 调整对比度和亮度（扫描仪通常会影响这些）
    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(random.uniform(1.0, 1.2))

    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(random.uniform(0.9, 1.1))

    # 3. 添加轻微模糊（模拟扫描的焦点问题）
    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))

    # 4. 添加噪点（模拟扫描仪噪声）
    img_array = np.array(image)
    noise = np.random.normal(0, 5, img_array.shape)
    noisy_img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(noisy_img_array)

    # 5. 添加轻微的纸张纹理（可选）
    # 创建一个轻微的纸张纹理
    paper_texture = Image.new('RGB', image.size, (250, 250, 250))
    texture_noise = np.random.normal(0, 3, np.array(paper_texture).shape)
    texture_array = np.clip(np.array(paper_texture) + texture_noise, 0, 255).astype(np.uint8)
    paper_texture = Image.fromarray(texture_array)

    # 混合纹理和图像（轻微的）
    image = Image.blend(paper_texture, image, 0.95)

    # 6. 可选：添加轻微的JPEG压缩痕迹
    # 保存为低质量JPEG再重新加载
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        temp_jpg = tmp.name
        image.save(temp_jpg, format='JPEG', quality=75)
        image = Image.open(temp_jpg)
        image.load()

    # 删除临时文件
    os.unlink(temp_jpg)

    # 7. 轻微锐化以模拟扫描仪的过度锐化
    image = image.filter(ImageFilter.SHARPEN)

    return image


def pdf_to_scanned(input_pdf, output_pdf, dpi=300):
    """
    将PDF转换为看起来像扫描的版本

    参数:
        input_pdf: 输入PDF文件路径
        output_pdf: 输出PDF文件路径
        dpi: 图像分辨率，默认300
    """
    try:
        # 打开原始PDF
        pdf_document = fitz.open(input_pdf)

        # 创建输出PDF
        output_document = fitz.open()

        # 处理每一页
        for page_num in range(len(pdf_document)):
            # 获取当前页
            page = pdf_document[page_num]

            # 将页面渲染为图像
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))

            # 将pixmap转换为PIL图像
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # 添加扫描效果
            scanned_img = add_scanner_effect(img)

            # 将处理后的图像转换回PDF页
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_img = tmp.name
                scanned_img.save(temp_img)

                # 插入新页面
                new_page = output_document.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(new_page.rect, filename=temp_img)

                # 删除临时文件
                os.unlink(temp_img)

        # 保存结果
        output_document.save(output_pdf)
        output_document.close()
        pdf_document.close()
        return True
    except Exception as e:
        print(f"处理PDF时出错: {e}")
        return False


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # 检查是否有文件上传
    if 'file' not in request.files:
        flash('没有上传文件')
        return redirect(request.url)

    file = request.files['file']

    # 如果用户没有选择文件
    if file.filename == '':
        flash('没有选择文件')
        return redirect(request.url)

    # 检查文件类型
    if file and allowed_file(file.filename):
        # 使用UUID生成唯一文件名
        filename = str(uuid.uuid4()) + '.pdf'
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 获取DPI设置
        dpi = int(request.form.get('dpi', 300))

        # 设置输出文件路径
        output_filename = str(uuid.uuid4()) + '_scanned.pdf'
        output_filepath = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)

        # 处理PDF
        if pdf_to_scanned(filepath, output_filepath, dpi):
            # 处理成功
            flash('PDF处理成功！')
            return redirect(url_for('success', filename=output_filename))
        else:
            # 处理失败
            flash('PDF处理失败，请检查文件是否有效')
            return redirect(url_for('index'))
    else:
        flash('只允许上传PDF文件')
        return redirect(request.url)


@app.route('/success/<filename>')
def success(filename):
    return render_template('success.html', filename=filename)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)


@app.route('/cleanup', methods=['POST'])
def cleanup():
    # 清理处理过的文件和上传的文件（可选功能）
    try:
        # 获取要删除的文件名
        filename = request.form.get('filename')
        if filename:
            # 删除处理后的文件
            processed_file = os.path.join(app.config['PROCESSED_FOLDER'], filename)
            if os.path.exists(processed_file):
                os.remove(processed_file)

        # 可以选择定期清理所有临时文件
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'清理文件时出错: {e}')
        return redirect(url_for('index'))


# 定期清理函数（可以通过定时任务调用）
def cleanup_old_files():
    """清理超过24小时的临时文件"""
    try:
        # 清理上传目录
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            if os.path.isfile(file_path) and (time.time() - os.path.getmtime(file_path)) > 86400:
                os.remove(file_path)

        # 清理处理目录
        for file in os.listdir(app.config['PROCESSED_FOLDER']):
            file_path = os.path.join(app.config['PROCESSED_FOLDER'], file)
            if os.path.isfile(file_path) and (time.time() - os.path.getmtime(file_path)) > 86400:
                os.remove(file_path)
    except Exception as e:
        print(f"清理旧文件时出错: {e}")


if __name__ == '__main__':
    # 在启动时检查目录
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    # 设置Debug模式为True以便于开发
    app.run(debug=True)
