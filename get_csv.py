# -*- coding: utf-8 -*-
import os
import csv
import nrrd
import numpy as np
import pydicom
from scipy.ndimage import label, find_objects

# 定义处理单个患者文件夹的函数
def process_patient_folder(patient_folder):
    nrrd_file = None
    dicom_files = []

    # 查找NRRD文件和DICOM文件
    for root, dirs, files in os.walk(patient_folder):
        for file in files:
            if file.endswith('.seg.nrrd'):
                nrrd_file = os.path.join(root, file)
            elif file.endswith('.dcm'):
                dicom_files.append(os.path.join(root, file))
    
    if nrrd_file is None or not dicom_files:
        return []

    # 读取NRRD文件
    data, header = nrrd.read(nrrd_file)

    # 转换数据的维度顺序，从 (512, 512, 287) 到 (287, 512, 512)
    data = np.transpose(data, (2, 0, 1))

    # 获取元数据
    origin = np.array(header['space origin'])
    spacing = np.array([direction[:3] for direction in header['space directions']])

    # 二值化数据，假设结节用1表示
    binary_data = data > 0

    # 标记连通区域
    labeled_array, num_features = label(binary_data)

    # 找到每个结节的边界框
    slices = find_objects(labeled_array)

    # 读取DICOM文件，提取相关元数据
    dicom_data = pydicom.dcmread(dicom_files[0])
    series_uid = dicom_data.SeriesInstanceUID
    pixel_spacing = dicom_data.PixelSpacing
    image_position_patient = dicom_data.ImagePositionPatient
    image_orientation_patient = dicom_data.ImageOrientationPatient
    slice_thickness = dicom_data.SliceThickness

    # 计算方向向量
    row_direction_vector = np.array(image_orientation_patient[0:3])
    column_direction_vector = np.array(image_orientation_patient[3:6])
    slice_direction_vector = np.cross(row_direction_vector, column_direction_vector)

    # 用于存储结节信息的列表
    nodules = []

    # 遍历每个结节，提取中心点和直径信息
    for i, slice in enumerate(slices):
        if slice is not None:
            # 计算结节的中心点
            center = [(s.start + s.stop - 1) / 2 for s in slice]
            diameter_mm = np.max([s.stop - s.start for s in slice]) * spacing[0][0]

            # 将体素坐标转换为世界坐标系
            voxel_coord = np.array(center)
            world_coord = (
                origin +
                voxel_coord[0] * slice_thickness * slice_direction_vector +
                voxel_coord[1] * pixel_spacing[0] * row_direction_vector +
                voxel_coord[2] * pixel_spacing[1] * column_direction_vector
            )

            # 存储结节信息
            nodules.append({
                'seriesuid': series_uid,
                'coordX': world_coord[0],
                'coordY': world_coord[1],
                'coordZ': world_coord[2],
                'diameter_mm': diameter_mm
            })

    return nodules

# 定义处理所有患者文件夹的函数
def process_all_patients(patients_folder, output_csv):
    all_nodules = []

    # 遍历每个患者文件夹
    for patient_folder in os.listdir(patients_folder):
        patient_path = os.path.join(patients_folder, patient_folder)
        if os.path.isdir(patient_path):
            nodules = process_patient_folder(patient_path)
            all_nodules.extend(nodules)

    # 保存所有结节信息到CSV文件
    csv_columns = ['seriesuid', 'coordX', 'coordY', 'coordZ', 'diameter_mm']
    
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()
        for data in all_nodules:
            writer.writerow(data)

    print(f"All nodules' world coordinates saved to {output_csv}")

# 设置路径
patients_folder = 'C:/Users/Hannn/Desktop/after/bbb'  # 替换为实际的patients文件夹路径
output_csv = 'C:/Users/Hannn/Desktop/after/result/nodules7.csv'  # 替换为实际的输出CSV文件路径

# 处理所有患者文件夹
process_all_patients(patients_folder, output_csv)