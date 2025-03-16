import os
import filecmp

def compare_folders(folder1, folder2):
    """
    Compare files in two folders by name and content.
    Reports files that exist in both but have different content.
    """
    files1 = set(os.listdir(folder1))
    files2 = set(os.listdir(folder2))

    # Find common files by name
    common_files = files1 & files2
    only_in_folder1 = files1 - files2
    only_in_folder2 = files2 - files1
    mismatched_files = []

    # Compare content of common files
    for file in common_files:
        file1_path = os.path.join(folder1, file)
        file2_path = os.path.join(folder2, file)

        # Ensure it's a file (not a folder)
        if os.path.isfile(file1_path) and os.path.isfile(file2_path):
            if not filecmp.cmp(file1_path, file2_path, shallow=False):
                mismatched_files.append(file)

    # Report results
    print("\n🔍 **Comparison Results** 🔍")
    if only_in_folder1:
        print(f"❌ Files only in {folder1}: {only_in_folder1}")
    if only_in_folder2:
        print(f"❌ Files only in {folder2}: {only_in_folder2}")
    if mismatched_files:
        print(f"⚠️  Files with the same name but different content: {mismatched_files}")
    else:
        print("✅ All matched files have identical content.")

if __name__ == "__main__":
    folder1 = "C:\Games\Reforgerator_onlysource\pytoshop"
    folder2 = "C:\Python312\Lib\site-packages\pytoshop"

    if os.path.isdir(folder1) and os.path.isdir(folder2):
        compare_folders(folder1, folder2)
    else:
        print("❌ One or both of the paths are not valid directories.")