import os
from datetime import datetime, timedelta

def create_backup_files():
    # 创建备份目录
    backup_dir = "backdir"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"创建备份目录: {backup_dir}")

    # 设置起始日期和结束日期
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 12, 31)
    
    # 数据库名称
    dbs = ["finance", "sales"]
    
    # 生成每天的备份文件
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        month_str = current_date.strftime("%m")
        
        for db in dbs:
            filename = f"{db}_{month_str}_{date_str}.sql"
            filepath = os.path.join(backup_dir, filename)
            
            # 创建空文件
            open(filepath, 'a').close()
            print(f"创建备份文件: {filename}")
            
        current_date += timedelta(days=1)

if __name__ == "__main__":
    create_backup_files() 