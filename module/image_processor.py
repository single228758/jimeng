import os
import io
import time
import requests
from PIL import Image
from common.log import logger
from io import BytesIO
import math

class ImageProcessor:
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        self.image_data = {}  # 初始化图片数据字典
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

    def ensure_temp_dir(self):
        """确保临时目录存在"""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def combine_images(self, urls):
        """将多张图片合并为一张2x2的图片
        Args:
            urls: 图片URL列表
        Returns:
            file: 合并后的图片文件对象
        """
        try:
            # 确保临时目录存在
            self.ensure_temp_dir()
            
            # 获取所有图片
            pil_images = []
            for url in urls[:4]:  # 最多处理4张图片
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    img_data = BytesIO(response.content)
                    img = Image.open(img_data)
                    pil_images.append(img)
                else:
                    logger.error(f"[Jimeng] Failed to download image from {url}")
                    return None

            if not pil_images:
                logger.error("[Jimeng] No valid images to combine")
                return None
            
            # 等比例缩放图片
            target_size = (512, 512)  # 目标尺寸
            resized_images = []
            for img in pil_images:
                # 计算缩放比例
                width, height = img.size
                ratio = min(target_size[0] / width, target_size[1] / height)
                new_size = (int(width * ratio), int(height * ratio))
                
                # 缩放图片
                resized = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # 创建白色背景
                padded = Image.new('RGB', target_size, 'white')
                
                # 将缩放后的图片居中粘贴
                x = (target_size[0] - new_size[0]) // 2
                y = (target_size[1] - new_size[1]) // 2
                padded.paste(resized, (x, y))
                
                resized_images.append(padded)
            
            # 计算合并图片的布局
            num_images = len(resized_images)
            if num_images == 1:
                cols, rows = 1, 1
            elif num_images == 2:
                cols, rows = 2, 1
            elif num_images <= 4:
                cols, rows = 2, 2
            else:
                cols = math.ceil(math.sqrt(num_images))
                rows = math.ceil(num_images / cols)
            
            # 创建空白画布，添加边距
            margin = 2  # 分割线宽度
            canvas_width = cols * target_size[0] + (cols - 1) * margin
            canvas_height = rows * target_size[1] + (rows - 1) * margin
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            # 粘贴图片到画布
            for idx, img in enumerate(resized_images):
                x = (idx % cols) * (target_size[0] + margin)
                y = (idx // cols) * (target_size[1] + margin)
                canvas.paste(img, (x, y))
            
            # 保存合并后的图片
            output_path = os.path.join(self.temp_dir, f"combined_{int(time.time())}.jpg")
            canvas.save(output_path, 'JPEG', quality=95)
            logger.info(f"[Jimeng] Successfully saved combined image to {output_path}")
            
            # 返回文件对象
            return open(output_path, 'rb')
            
        except Exception as e:
            logger.error(f"[Jimeng] Error combining images: {e}")
            return None
        finally:
            # 清理PIL图片对象
            for img in pil_images:
                try:
                    img.close()
                except:
                    pass

    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.warning(f"[Jimeng] Error deleting {file_path}: {e}")
            logger.info("[Jimeng] Cleaned up temporary files")
        except Exception as e:
            logger.error(f"[Jimeng] Error cleaning up temporary files: {e}")

    def store_image_data(self, image_urls, operation_type, parent_id=None):
        """存储图片信息"""
        img_id = str(int(time.time()))
        self.image_data[img_id] = {
            "urls": image_urls,
            "timestamp": time.time(),
            "operation": operation_type
        }
        if parent_id:
            self.image_data[img_id]["parent_id"] = parent_id
        return img_id

    def get_image_data(self, img_id):
        """获取图片信息"""
        return self.image_data.get(img_id)

    def validate_image_index(self, img_id, index):
        """验证图片索引的有效性"""
        image_data = self.get_image_data(img_id)
        if not image_data:
            return False, "找不到对应的图片ID"
        if not image_data.get("urls"):
            return False, "找不到图片数据"
        if index > len(image_data["urls"]):
            return False, f"图片索引超出范围，当前只有{len(image_data['urls'])}张图片"
        return True, None 

    def save_combined_image(self, images, output_path=None):
        """将多张图片合并为一张图片并保存
        Args:
            images: 图片列表(每个元素可以是PIL.Image对象、文件路径或URL)
            output_path: 输出文件路径,如果为None则使用临时文件
        Returns:
            file: 保存的图片文件对象
        """
        try:
            # 如果没有指定输出路径，使用临时文件
            if not output_path:
                output_path = os.path.join(self.temp_dir, f"combined_{int(time.time())}.jpg")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 获取所有图片
            pil_images = []
            for img in images:
                if isinstance(img, Image.Image):
                    pil_images.append(img)
                elif isinstance(img, str):
                    if img.startswith(('http://', 'https://')):
                        # 下载URL图片
                        response = requests.get(img, timeout=30)
                        img_data = BytesIO(response.content)
                        pil_images.append(Image.open(img_data))
                    else:
                        # 加载本地图片
                        pil_images.append(Image.open(img))
                elif isinstance(img, bytes):
                    # 从字节数据加载图片
                    img_data = BytesIO(img)
                    pil_images.append(Image.open(img_data))
                elif hasattr(img, 'read'):
                    # 从文件对象加载图片
                    pil_images.append(Image.open(img))
            
            if not pil_images:
                logger.error("[Jimeng] No valid images to combine")
                return None
            
            # 调整所有图片大小为相同尺寸
            target_size = (512, 512)  # 可以根据需要调整
            resized_images = [img.resize(target_size) for img in pil_images]
            
            # 计算合并图片的布局
            num_images = len(resized_images)
            if num_images == 1:
                cols, rows = 1, 1
            elif num_images == 2:
                cols, rows = 2, 1
            elif num_images <= 4:
                cols, rows = 2, 2
            else:
                cols = math.ceil(math.sqrt(num_images))
                rows = math.ceil(num_images / cols)
            
            # 创建空白画布
            canvas_width = cols * target_size[0]
            canvas_height = rows * target_size[1]
            canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
            
            # 粘贴图片到画布
            for idx, img in enumerate(resized_images):
                x = (idx % cols) * target_size[0]
                y = (idx // cols) * target_size[1]
                canvas.paste(img, (x, y))
            
            # 保存合并后的图片
            canvas.save(output_path, 'JPEG', quality=95)
            logger.info(f"[Jimeng] Successfully saved combined image to {output_path}")
            
            # 返回文件对象
            return open(output_path, 'rb')
            
        except Exception as e:
            logger.error(f"[Jimeng] Error combining images: {e}")
            return None
        finally:
            # 清理PIL图片对象
            for img in pil_images:
                try:
                    img.close()
                except:
                    pass 