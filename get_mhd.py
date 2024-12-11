# coding=UTF-8
import os
import pydicom
import numpy
import SimpleITK
import logging
 
 
# 路径和列表声明
rootpath="/home/bbb/shaobo/DCM"
SaveRawDicom = "/home/bigspace/shaobo/mhd"  # 与python文件同一个目录下的文件夹,用来存储mhd文件和raw文件
def getSubPaths(dir):
    list = []
    # 判断路径是否存在
    if (os.path.exists(dir)):
        # 获取该目录下的所有文件或文件夹目录
        files = os.listdir(dir)
        for file in files:
            # 得到该文件下所有目录的路径
            m = os.path.join(dir, file)
            # 判断该路径下是否是文件夹
            if (os.path.isdir(m)):
                list.append(m)
    return list

def parse_single_dcm(dicom_name):#确保是原始ＨＵ值
    """
    Parse info from a single dicom
    :param dicom_name: target dicom file
    :return:
        slice: 2D numpy array
        dicom: a class-like struct
    """
    dicom = pydicom.read_file(dicom_name)  # pydicom return a class-like struct

    # rescale intercept and slope
    slice = dicom.pixel_array
    try:
        intercept = dicom.RescaleIntercept
        slope = dicom.RescaleSlope
    except AttributeError:
        intercept = 0
        slope = 1
        logging.warning('rescale info missing.')
    finally:
        slice = slice * slope + intercept

    return slice, dicom

def sliceInstanceNumber(fileList,dirName):
    list=[]
    for filename in fileList:
        if ".dcm" in filename.lower():
            path=os.path.join(dirName, filename)
            dicom = pydicom.read_file(path)
            dcmID = dicom.InstanceNumber
            list.append([path,dcmID])
    return list

def get_mhd_raw(PathDicom,SaveRawDicom):
    lstFilesDCM = []
    
    # 将PathDicom文件夹下的dicom文件地址读取到lstFilesDCM中
    for dirName, subdirList, fileList in os.walk(PathDicom):
        ll = sliceInstanceNumber(fileList, PathDicom)  # sort for sliceInstanceNumber
        ll.sort(key=lambda x: x[1])  #排序了（不然放进去的是乱序）
        for filename in ll:
            if ".dcm" in filename[0].lower():  # 判断文件是否为dicom文件
                #print(filename)
                lstFilesDCM.append(filename[0])  # 加入到列表中

    # 第一步：将第一张图片作为参考图片，并认为所有图片具有相同维度
    dcm_pixel_array, RefDs = parse_single_dcm(lstFilesDCM[0])
    # 第二步：得到dicom图片所组成3D图片的维度
    ConstPixelDims = (int(RefDs.Rows), int(RefDs.Columns), len(lstFilesDCM))  # ConstPixelDims是一个元组

    # 第三步：得到x方向和y方向的Spacing并得到z方向的层厚
    ConstPixelSpacing = (float(RefDs.PixelSpacing[0]), float(RefDs.PixelSpacing[1]), float(RefDs.SliceThickness))

    # 第四步：得到图像的原点
    #Origin = RefDs.ImagePositionPatient

    # 第五步：得到序列名称用于命名
    Seriesname = RefDs.SeriesInstanceUID

    # 病人ID
    AccessionNumber = RefDs.AccessionNumber
    PatientID = RefDs.PatientID
    StudyInstanceUID = RefDs.StudyInstanceUID
    # print("pid",Seriesname)
    # dcmID = RefDs.SOPInstanceUID#根据dcmid排序
    # print("dcmid",dcmID)

    # 根据维度创建一个numpy的三维数组，并将元素类型设为：pixel_array.dtype

    ArrayDicom = numpy.zeros(ConstPixelDims, dtype=dcm_pixel_array.dtype)  # 要注意定义零矩阵时的数据类型。
    # 第五步:遍历所有的dicom文件，读取图像数据，存放在numpy数组中
    #i = 0
    #遍历所有的dicom文件，并把每个parse_single_dcm返回的dicom存放在DS中
    #for filenameDCM in lstFilesDCM:
        # ds = pydicom.read_file(filenameDCM)#里面的矩阵数据已经可能被调整过
        #data, ds = parse_single_dcm(filenameDCM)
        #ArrayDicom[:, :, lstFilesDCM.index(filenameDCM)] = data
        #i += 1
    dcm_files = [s for s in os.listdir(PathDicom) if s.endswith('.dcm')]
    #dicom = pydicom.read_file(s)
    slices = [pydicom.read_file(os.path.join(PathDicom, s)) for s in dcm_files]
    slices.sort(key=lambda x: float(x.ImagePositionPatient[2]))
    for s in slices:
        slicer=s.pixel_array
        try:
            intercept = s.RescaleIntercept
            slope = s.RescaleSlope
        except AttributeError:
            intercept = 0
            slope = 1
            logging.warning('rescale info missing.')
        finally:
            slicer = slicer * slope + intercept
        ArrayDicom[:, :, slices.index(s)] = slicer
    
    Origin = slices[0].ImagePositionPatient
    # 第六步：对numpy数组进行转置，即把坐标轴（x,y,z）变换为（z,y,x）,这样是dicom存储文件的格式，即第一个维度为z轴便于图片堆叠
    ArrayDicom = numpy.transpose(ArrayDicom,
                                 (2, 0, 1))  # 有点疑问不应该是(xyz)变为(zxy)么??##其实是zxy,但是x是行,y是列.在plt时(列,行),故类比zyx.
    # 第七步：将现在的numpy数组通过SimpleITK转化为mhd和raw文件
    sitk_img = SimpleITK.GetImageFromArray(ArrayDicom, isVector=False)
    sitk_img = SimpleITK.Cast(sitk_img, SimpleITK.sitkInt16)
    sitk_img.SetSpacing(ConstPixelSpacing)
    sitk_img.SetOrigin(Origin)
    #if 'WindowCenter' in RefDs:
        #sitk_img.SetMetaData('WindowCenter', str(RefDs.WindowCenter))
    #if 'WindowWidth' in RefDs:
        #sitk_img.SetMetaData('WindowWidth', str(RefDs.WindowWidth))
    SimpleITK.WriteImage(sitk_img, os.path.join(SaveRawDicom, Seriesname + ".mhd"))
    print('done')



if __name__ == '__main__':

    list_classes = getSubPaths(rootpath)
    lc=getSubPaths('/home/bigspace/shaobo/huaxi')
    for i in range(len(lc)):
        PathDicom=lc[i]
        try:
            get_mhd_raw(PathDicom,SaveRawDicom)
        except:
            print('%s文件夹下是空'%PathDicom)