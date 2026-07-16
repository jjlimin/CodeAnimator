import json
import boto3
import os
import subprocess
import imageio_ffmpeg  # שכבת ffmpeg-layer — מספקת בינארי ffmpeg סטטי

# ffmpeg לא קיים בסביבת הריצה של למבדה; משתמשים בבינארי שמגיע עם השכבה
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')

BUCKET_NAME = 'code-animator-media-bucket-2026'
TABLE_NAME = 'CodeAnimatorJobs'

def lambda_handler(event, context):
    # ה-Step Function מעביר לנו מערך של תוצאות מה-Map State
    # אנחנו צריכים לחלץ את ה-job_id מתוך האירוע הראשון
    if not event:
        raise ValueError("Event is empty")

    # ה-Map מוגדר עם ResultPath: null, ולכן האירוע שמגיע לכאן הוא הפלט של
    # AIAgent (מילון עם job_id) ולא רשימה. תומכים בשני המבנים ליתר ביטחון.
    first_item = event[0] if isinstance(event, list) else event
    job_id = first_item.get('job_id')
    
    if not job_id:
        raise ValueError("Missing job_id in event")
        
    print(f"Starting concatenation for job: {job_id}")
    
    # 1. שליפת רשימת כל הקבצים ששייכים ל-Job הזה ב-S3
    prefix = f"jobs/{job_id}/scenes/"
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    
    if 'Contents' not in response:
        raise Exception(f"No rendered scenes found in S3 for job {job_id}")
        
    # סינון ומיון הקבצים לפי סדר הסצנות (scene_0, scene_1...)
    scene_keys = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.mp4')]
    scene_keys.sort() # מיון אלפביתי מבטיח שסצנה 0 תהיה לפני סצנה 1
    
    tmp_dir = '/tmp'
    list_file_path = os.path.join(tmp_dir, 'files.txt')
    output_video_path = os.path.join(tmp_dir, 'final_output.mp4')
    
    # 2. הורדת כל הקבצים המקומיים ויצירת קובץ טקסט עבור FFmpeg
    downloaded_files = []
    with open(list_file_path, 'w') as f:
        for idx, key in enumerate(scene_keys):
            local_path = os.path.join(tmp_dir, f'scene_{idx}.mp4')
            print(f"Downloading {key} to {local_path}...")
            s3.download_file(BUCKET_NAME, key, local_path)
            downloaded_files.append(local_path)
            # כתיבת הנתיב לקובץ הטקסט בפורמט ש-FFmpeg מבין
            f.write(f"file '{local_path}'\n")
            
    # 3. הרצת פקודת FFmpeg לחיבור מהיר (בלי Re-encoding)
    print("Running FFmpeg concat...")
    try:
        subprocess.run([
            FFMPEG_EXE, '-y', '-f', 'concat', '-safe', '0',
            '-i', list_file_path, '-c', 'copy', output_video_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode('utf-8')}")
        raise e
        
    # 4. העלאת הקובץ הסופי ל-S3
    final_s3_key = f"jobs/{job_id}/final_output.mp4"
    s3.upload_file(
        output_video_path, 
        BUCKET_NAME, 
        final_s3_key,
        ExtraArgs={"ContentType": "video/mp4"}
    )
    
    # כתובת ה-URL הציבורית של הסרטון (במידה והבאקט מאפשר גישה)
    video_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{final_s3_key}"
    
    # 5. עדכון הסטטוס ב-DynamoDB ל-COMPLETED
    dynamodb.update_item(
        TableName=TABLE_NAME,
        Key={'job_id': {'S': job_id}},
        UpdateExpression="SET #st = :s, video_url = :u",
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={
            ':s': {'S': 'COMPLETED'},
            ':u': {'S': video_url}
        }
    )
    
    # 6. ניקוי קבצים זמניים
    os.remove(list_file_path)
    os.remove(output_video_path)
    for file in downloaded_files:
        os.remove(file)
        
    print(f"Job {job_id} completed successfully!")
    return {
        "statusCode": 200,
        "job_id": job_id,
        "video_url": video_url
    }