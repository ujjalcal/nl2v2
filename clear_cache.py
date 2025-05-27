import os
import shutil

def clear_temp_folder():
    """Clear all files in the temp folder and its subfolders"""
    temp_folder = 'temp'
    
    if os.path.exists(temp_folder):
        # Clear the contents of the temp folder
        for item in os.listdir(temp_folder):
            item_path = os.path.join(temp_folder, item)
            
            if os.path.isdir(item_path):
                # For directories, clear their contents but keep the directory
                for subitem in os.listdir(item_path):
                    subitem_path = os.path.join(item_path, subitem)
                    if os.path.isfile(subitem_path):
                        os.remove(subitem_path)
                    elif os.path.isdir(subitem_path):
                        shutil.rmtree(subitem_path)
                print(f"Cleared contents of {item_path}")
            elif os.path.isfile(item_path):
                os.remove(item_path)
                print(f"Removed file {item_path}")
        
        print("Cache cleared successfully")
    else:
        print(f"Temp folder '{temp_folder}' does not exist")

if __name__ == "__main__":
    clear_temp_folder()
