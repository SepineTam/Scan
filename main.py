#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 - present Sepine Tam, Inc. All Rights Reserved
#
# @Author : Sepine Tam
# @Email  : sepinetam@gmail.com
# @File   : main.py

import os
import random
import argparse
import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np
from pathlib import Path
import tempfile


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
    # 打开原始PDF
    pdf_document = fitz.open(input_pdf)

    # 创建输出PDF
    output_document = fitz.open()

    print(f"处理PDF，共 {len(pdf_document)} 页")

    # 处理每一页
    for page_num in range(len(pdf_document)):
        print(f"处理第 {page_num + 1} 页...")

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
    print(f"处理完成！扫描效果PDF已保存为: {output_pdf}")


def main():
    parser = argparse.ArgumentParser(description='将PDF文件转换为看起来像扫描稿的效果')
    parser.add_argument('input_pdf', help='输入PDF文件路径')
    parser.add_argument('-o', '--output', help='输出PDF文件路径（默认为原文件名+_scanned.pdf）')
    parser.add_argument('-d', '--dpi', type=int, default=300, help='图像处理分辨率（默认300）')

    args = parser.parse_args()

    input_path = Path(args.input_pdf)

    if not input_path.exists():
        print(f"错误：文件 '{input_path}' 不存在")
        return

    if args.output:
        output_path = args.output
    else:
        output_path = input_path.with_stem(f"{input_path.stem}_scanned").with_suffix('.pdf')

    pdf_to_scanned(str(input_path), str(output_path), args.dpi)


if __name__ == "__main__":
    main()
