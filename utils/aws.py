import boto3, uuid, os, mimetypes

class S3ImgUploader:
    """
        AWS_ACCESS_KEY 및 AWS_SECRET_ACCESS_KEY 환경변수 설정 필요
    """
    def __init__(self, file):
        self.file = file

    def upload(self):
        return self.__upload()
    
    def upload_review_img(self, review_id:int=0):
        dir = f"{review_id}/" if review_id > 0 else ""
        return self.__upload(f'reviews/{dir}')
    
    def upload_restaurant_img(self, restaurant_id:int=0):
        dir = f"{restaurant_id}/" if restaurant_id > 0 else ""
        return self.__upload(f'restaurants/{dir}')
        
    def delete(self, url):
        s3_client = boto3.client(
            's3',
            aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        )
        
        s3_client.delete_object(Bucket="yumyum-s3-bucket", Key=url)
        
        
    def __upload(self, dir:str=""):
        s3_client = boto3.client(
            's3',
            aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        )
        
        content_type, _ = mimetypes.guess_type(self.file.name)
        file_name, _ = os.path.splitext(os.path.basename(self.file.name))
        url = 'img/'+dir+file_name+'_'+uuid.uuid1().hex
        s3_client.upload_fileobj(
            self.file, 
            "yumyum-s3-bucket", 
            url, 
            ExtraArgs={"ContentType": content_type}
        )
        return url
