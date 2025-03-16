import os
import shutil
import subprocess
import pyminizip
import var.global_var as gv # Import global variables (PROGRAM_NAME, PROGRAM_VERSION)
import datetime
import textwrap
import re

# Names
program_name = gv.PROGRAM_NAME.replace(" ", "_")
program_name_exe = f"{program_name}.exe"
program_version = gv.PROGRAM_VERSION.replace(" ", "_")
appdata_files = [gv.FILE_USER_CONFIG,]

# Relatives paths
data_folder_rel = "data"
templates_folder_rel="templates"
unwanted_items_from_data_rel = [
    gv.DIRS["output"],
    os.path.join(gv.DIRS["config"],gv.FILE_USER_CONFIG),
]
empty_folders_rel = [gv.DIRS["output"],]
unistaller_bat = "uninstall.bat"
source_file = "main.py"
README_txt_file = "README.txt"
README_md_file = "README.md"
specific_files_rel = ["LICENSE", README_txt_file ]
icon_file_rel = os.path.join(data_folder_rel, "logo.ico")

# Abs paths
base_dir_abs = os.path.dirname(os.path.abspath(__file__))
dist_folder_abs = os.path.join(base_dir_abs, "dist")
build_dir_abs = os.path.join(base_dir_abs, "dist")
exe_build_abs = os.path.join(build_dir_abs,program_name_exe)
spec_file_abs = os.path.join(base_dir_abs, "main.spec")
spec_file_template_abs = os.path.join(base_dir_abs, templates_folder_rel,"main.spec_template.txt")
readme_txt_template_file_abs=os.path.join(base_dir_abs, templates_folder_rel,"README_template_txt.txt")
readme_md_template_file_abs=os.path.join(base_dir_abs, templates_folder_rel,"README_template_md.txt")
changelog_file_abs = os.path.join(base_dir_abs,templates_folder_rel,"changelog.txt")
credits_file_abs = os.path.join(base_dir_abs,data_folder_rel,gv.DIRS["credits"], "credits.txt")
localisation_dir_abs = os.path.join(base_dir_abs,data_folder_rel,gv.DIRS["localisations"])

# We assume this script is run from the folder in which main.spec and gv.py are located.
# For safety, we use the absolute path of this script's directory to ensure we only operate within it.
def main():
    password = "makkad"
    output_zip_abs =os.path.join(dist_folder_abs,f"{program_name}_{program_version}.zip")

    # 0)
    create_readme(readme_md_template_file_abs,README_md_file,False)
    create_readme(readme_txt_template_file_abs,README_txt_file,True)

    # 1) Create .spec from template
    update_spec_file(spec_file_template_abs,spec_file_abs)

    # 2) Clear current dist folder, ensuring we delete only within 'dist_folder'
    clear_dist_folder(dist_folder_abs)

    # 3) Run pyinstaller main.spec
    run_pyinstaller(spec_file_abs)
    #run_nuitka(source_file)

    # 4) Copy directories (e.g., assets, configs) into dist while preserving structure. Do not copy unwanted_folders
    copied_folders, copied_files = copy_from_data(dist_folder_abs,data_folder_rel,unwanted_items_from_data_rel)  # Add or change as needed

    # 5) Create empty folders in dist
    create_empty_folders(dist_folder_abs,empty_folders_rel)  # Add or change as needed

    # 6) Copy specific files into dist
    copy_specific_files(dist_folder_abs, specific_files_rel)  # Add or change as needed

    # 7) Remove specific unwanted files from dist
    #remove_unwanted_files(dist_folder_abs,unwanted_files)  # Add or change as needed

    # 8) Build uninstaller
    all_files = copied_files + specific_files_rel
    create_batch_uninstaller(
        dist_folder=dist_folder_abs,
        exe_name=f"{program_name}.exe",
        extra_dirs=copied_folders,
        empty_dirs=empty_folders_rel,
        specific_files=all_files,
        appdata_files=appdata_files,
    )

    # 9) Create a zip archive of the dist folder
    create_zip_archive(dist_folder_abs, output_zip_abs, password)
    print(f"Build process completed. Archive created: {output_zip_abs}")


def update_spec_file(spec_file_template_abs,spec_file_abs):
    """Update the main.spec file to modify the EXE name."""
    if not os.path.exists(spec_file_template_abs):
        print(f"Warning: {spec_file_template_abs} does not exist.")
        return

    new_lines = []
    with open(spec_file_template_abs, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip().startswith("name="):
                new_lines.append(f"    name='{program_name}',\n")
            elif line.strip().startswith("icon="):
                new_lines.append(f"    icon='{icon_file_rel.replace('\\','/')}',\n")
            else:
                new_lines.append(line)

    with open(spec_file_abs, "w", encoding="utf-8") as file:
        file.writelines(new_lines)


def clear_dist_folder(dist_path):
    """Safely clear the dist folder by removing only child items."""
    if not os.path.exists(dist_path):
        return

    for item in os.listdir(dist_path):
        item_path = os.path.join(dist_path, item)

        # Double-check we only remove items if they are inside dist_path
        if not item_path.startswith(os.path.abspath(dist_path)):
            print(f"Skipping deletion of {item_path}, as it's outside {dist_path}.")
            continue

        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"Warning: Could not delete {item_path}: {e}")


def run_pyinstaller(spec_file_path):
    """Run PyInstaller with the provided spec file."""
    subprocess.run(["pyinstaller", spec_file_path], check=True)

def run_nuitka(source_file):
    """Run Nuitka to compile the provided Python file into an executable."""

    # Copy the environment and remove PYTHONHOME before starting the subprocess
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)  # Remove PYTHONHOME if it exists

    subprocess.run([
        "python", "-m", "nuitka",
        "--msvc=latest",# Visual Studio 2022 or higher. Use the default English language pack to enable Nuitka to filter away irrelevant outputs and, therefore, have the best results
        "--standalone",  # Ensures all dependencies are included
        "--onefile",  # Optional: Creates a single executable
        "--include-module=wx._xml",
        "--windows-disable-console",  # Optional: Keeps the console open (remove for GUI apps)
        "--windows-icon-from-ico=logo.ico",
        f"--output-dir={build_dir_abs}",  # Set output directory
        f"--output-filename={program_name_exe}",
        source_file
    ], check=True)

    # Copy the environment and remove PYTHONHOME before starting the subprocess
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)  # Remove PYTHONHOME if it exists

def copy_from_data(dist_folder, data_folder, unwanted_items):
    """
    Copy the directory structure from data_folder into dist_folder,
    preserving the tree structure while excluding any files or directories
    whose relative paths (from data_folder) match or lie under any entry
    in unwanted_items.
    Args:
        dist_folder (str): Destination folder (relative path).
        data_folder (str): Source folder containing data (relative path).
        unwanted_items (list): List of relative paths (files or folders)
            to be excluded from the copy.
    Returns:
        2 lists: top-level folders and files (names relative to dist_folder) that were copied.
              These are the base names from data_folder (excluding unwanted items).
    Notes:
        For safety, all operations use an absolute base_dir computed from the location
        of this file.
    """
    # Define the base directory for safety operations
    base_dir = base_dir_abs

    # Compute the absolute paths for the source and destination folders.
    if not os.path.isabs(data_folder):
        abs_data_folder = os.path.join(base_dir, data_folder)
    else:
        abs_data_folder = data_folder
    if not os.path.isabs(dist_folder):
        abs_dist_folder = os.path.join(base_dir, dist_folder)
    else:
        abs_dist_folder = dist_folder

    # Ensure the destination folder exists.
    if not os.path.exists(abs_dist_folder):
        os.makedirs(abs_dist_folder)

    # Helper function: check if a given relative path should be excluded.
    def is_unwanted(rel_path):
        # Normalize the relative path for consistency.
        norm_rel_path = os.path.normpath(rel_path)
        for unwanted in unwanted_items:
            norm_unwanted = os.path.normpath(unwanted)
            # Check if the current item exactly matches or lies under an unwanted path.
            if norm_rel_path == norm_unwanted or norm_rel_path.startswith(norm_unwanted + os.sep):
                return True
        return False

    copied_files = []
    copied_folders = []

    # Loop through all top-level items in the source directory.
    for item in os.listdir(abs_data_folder):
        # For top-level, the relative path is just the item's name.
        rel_item = item
        if is_unwanted(rel_item):
            continue

        abs_item = os.path.join(abs_data_folder, item)
        abs_dest = os.path.join(abs_dist_folder, item)

        # If it's a directory, use copytree with an ignore function.
        if os.path.isdir(abs_item):
            def ignore_func(current_dir, contents):
                # Calculate the relative path of the current directory from the data_folder.
                rel_dir = os.path.relpath(current_dir, abs_data_folder)
                to_ignore = []
                # Check each file/subdirectory in the current directory.
                for name in contents:
                    candidate_rel = os.path.normpath(os.path.join(rel_dir, name))
                    if is_unwanted(candidate_rel):
                        to_ignore.append(name)
                return to_ignore

            shutil.copytree(abs_item, abs_dest, dirs_exist_ok=True, ignore=ignore_func)
            copied_folders.append(rel_item)
        # If it's a file, simply copy it.
        elif os.path.isfile(abs_item):
            shutil.copy2(abs_item, abs_dest)
            copied_files.append(rel_item)
        else:
            # Optionally, you can handle symlinks or other types here.
            print(f"Skipping unknown file type: {abs_item}")
            continue

        # Record the top-level item that was copied.
    return copied_folders, copied_files

def remove_unwanted_files(dist_folder, files_to_remove):
    """Remove specific files from the dist folder."""
    for file_name in files_to_remove:
        file_path = os.path.join(dist_folder, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print(f"Info: {file_name} not found in dist folder, skipping deletion.")

def create_zip_archive(dist_folder, output_zip, password):
    file_paths = []
    arc_names = []
    compression_level = 6

    for root, _, files in os.walk(dist_folder):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(root, dist_folder)
            if arcname==".":
             arcname=""
            file_paths.append(file_path)
            arc_names.append(arcname)

    if password:
        file_name=f"archive_password_{password}"
        file_path=os.path.join(dist_folder,file_name)
        with open(file_path, "w") as f:
            f.write(file_name)
        file_paths.append(file_path)
        arc_names.append("")

    # Create a password-protected zip archive.
    pyminizip.compress_multiple(file_paths, arc_names, output_zip, password, compression_level)

    if password and os.path.exists(file_path):
        os.remove(file_path)

def create_empty_folders(dist_folder, folders):
    """Create empty folders inside the dist folder."""
    for folder in folders:
        folder_path = os.path.join(dist_folder, folder)
        os.makedirs(folder_path, exist_ok=True)

def copy_specific_files(dist_folder, files):
    """Copy specific files into the dist folder."""
    base_dir = base_dir_abs
    for file in files:
        src = os.path.join(base_dir, file)
        dest = os.path.join(dist_folder, file)
        if os.path.exists(src):
            shutil.copy2(src, dest)
        else:
            print(f"Warning: File {file} not found!")

def create_batch_uninstaller(dist_folder, exe_name, extra_dirs, empty_dirs, specific_files, appdata_files):
    batch_template = r'''@echo off
    setlocal enabledelayedexpansion

    REM Confirm uninstallation
    set /p confirm="Are you sure you want to uninstall {exe_name}? (Y/N): "
    if /i "!confirm!" neq "Y" (
        echo Uninstallation cancelled by user.
        pause
        exit /b 0
    )

    REM Ensure executable exists before proceeding
    if not exist "%~dp0{exe_name}" (
        echo ERROR: {exe_name} not found in current directory. Aborting uninstallation.
        pause
        exit /b 1
    )

    REM Delete executable
    if exist "%~dp0{exe_name}" (
        del "%~dp0{exe_name}"
        echo Deleted executable: {exe_name}
    )

    REM Delete extra directories
    {extra_dirs_commands}

    REM Delete empty directories
    {empty_dirs_commands}

    REM Delete specific files
    {specific_files_commands}

    REM Delete appdata files
    {appdata_files_commands}

    REM Delete application AppData directory
    set APPDATA_DIR="%LOCALAPPDATA%\{program_name}\{program_name}"
    if exist !APPDATA_DIR! (
        rmdir /s /q !APPDATA_DIR!
        echo Deleted AppData directory: !APPDATA_DIR!
    )

    REM Delete application AppData directory
    set APPDATA_DIR="%LOCALAPPDATA%\{program_name}"
    if exist !APPDATA_DIR! (
        rmdir /s /q !APPDATA_DIR!
        echo Deleted AppData directory: !APPDATA_DIR!
    )

    echo Uninstallation completed successfully.
    pause

    REM Self-delete after the pause, outside current batch execution
    start /b cmd /c "timeout /t 1 >nul & del /f /q "%~f0""

    endlocal
    '''

    extra_dirs_commands = '\n'.join(
        [f'if exist "%~dp0{dir}" (rmdir /s /q "%~dp0{dir}" & echo Deleted directory: {dir})' for dir in extra_dirs]
    )

    empty_dirs_commands = "\n".join(
        [f'if exist "%~dp0{dir}" (rmdir /s /q "%~dp0{dir}" & echo Deleted directory: {dir})' for dir in empty_dirs]
    )

    specific_files_commands = "\n".join(
        [f'if exist "%~dp0{file}" (del "%~dp0{file}" & echo Deleted file: {file})' for file in specific_files]
    )

    appdata_files_commands = generate_appdata_delete_commands(appdata_files)

    batch_content = batch_template.format(
        exe_name=exe_name,
        extra_dirs_commands=extra_dirs_commands,
        empty_dirs_commands=empty_dirs_commands,
        specific_files_commands=specific_files_commands,
        appdata_files_commands=appdata_files_commands,
        program_name=gv.PROGRAM_NAME,
    )

    batch_path = os.path.join(dist_folder, unistaller_bat)
    with open(batch_path, 'w', encoding='utf-8') as batch_file:
        batch_file.write(batch_content)

    print(f"Batch uninstaller created at {batch_path}")

def generate_appdata_delete_commands(appdata_files):
    commands = []
    appdata_dir = os.path.join(r"%LOCALAPPDATA%", gv.PROGRAM_NAME,gv.PROGRAM_NAME)

    for file in appdata_files:
        file_path = os.path.join(appdata_dir, file)
        cmd = (
            f'if exist "{file_path}" (\n'
            f'    del "{file_path}"\n'
            f'    echo Deleted AppData file: {file}\n'
            ')'
        )
        commands.append(cmd)
    return "\n".join(commands)

def create_readme(readme_template,readme_output,txt):

    year = datetime.datetime.now().strftime("%Y")
    date = datetime.datetime.now().strftime("%d, %B %Y")

    # Load credits data from credits.txt
    credits_data = {}
    if os.path.isfile(credits_file_abs):
        with open(credits_file_abs, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    credits_data[key.strip()] = value.strip()

    # Process credit entries (split values by semicolon and remove empties)
    contributors = [x.strip() for x in credits_data.get("credit_contributors", "").split(";") if x.strip()]
    thanks       = [x.strip() for x in credits_data.get("credit_thanks_to", "").split(";") if x.strip()]
    community    = [x.strip() for x in credits_data.get("credit_community", "").split(";") if x.strip()]
    support      = [x.strip() for x in credits_data.get("credit_donat", "").split(";") if x.strip()]

    thanks_items = ", ".join(items for items in thanks)
    if txt:
        community_items = ", ".join(items for items in community)
        support_items = ", ".join(items for items in support)
    else:
        community_items = ", ".join( f"[{items}]({items})" for items in community)
        support_items = ", ".join(f"[{items}]({items})" for items in support)  

    # Define the list of available languages
    languages = []
    if os.path.isdir(localisation_dir_abs):
        files = os.listdir(localisation_dir_abs)
        # Filter for language files (e.g. local_eng.txt, local_rus.txt, etc.)
        lang_files = [f for f in files if f.startswith("local_") and f.endswith(".txt")]
        # Ensure the default language is always first
        lang_files.sort(key=lambda x: 0 if x == "local_eng.txt" else 1)
        for lang_file in lang_files:
            # Extract language code from file name: "local_eng.txt" -> "eng"
            lang_code = lang_file[len("local_"):-len(".txt")]
            try:
                with open(os.path.join(localisation_dir_abs, lang_file), "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                if first_line.lower().startswith("language"):
                    # Expecting format: language = English
                    parts = first_line.split("=", 1)
                    lang_name = parts[1].strip() if len(parts) > 1 else lang_file
                else:
                    lang_name = lang_file
            except Exception:
                lang_name = lang_file
            languages.append(lang_name)
               
    language_items = ", ".join(items for items in languages)

    with open(changelog_file_abs, "r", encoding="utf-8") as changelog_data:
        changelog = changelog_data.read()
    
    # Dictionary containing your tag replacements
    tag_replacements = {
    "<program-name>": gv.PROGRAM_NAME,
    "<PROGRAM-NAME>": gv.PROGRAM_NAME.upper(),
    "<date>": date,
    "<year>": year,
    "<author-name>": gv.PROGRAM_AUTHOR,
    "<uninstall>": unistaller_bat,
    "<version>": gv.PROGRAM_VERSION,
    "<credit_thanks>" : thanks_items,
    "<credit_community>" : community_items,
    "<credit_donat>" : support_items,
    "<language-list>" : language_items,
    "<changelog>" : changelog,
    "<custom_frames_folder>": gv.DIRS['custom_frames'].replace("\\","/")
    }

    # Read the template file
    with open(readme_template, "r", encoding="utf-8") as template_file:
        content = template_file.read()

    # Replace all tags with their corresponding values
    for tag, replacement in tag_replacements.items():
        content = content.replace(tag, replacement)

    if txt:
        content = wrap_full_text(content, limit=80)

    # Write the modified content to a new README.md file
    with open(readme_output, "w", encoding="utf-8") as output_file:
        output_file.write(content)

    print(f"{readme_output} has been created successfully.")


def wrap_line(line, limit):
    """
    Wrap a single line if it exceeds the specified limit.
    The original indent (all characters before the first alphabetical character)
    is preserved on the first line, and new lines receive an indent made from spaces
    with the same width as the original indent.
    """
    # Preserve blank lines
    if not line.strip():
        return line

    # Find the original indent: everything before the first alphabetical character.
    match = re.search(r'[A-Za-z]', line)
    if match:
        orig_indent = line[:match.start()]
    else:
        orig_indent = ""
    
    # Compute new indent for subsequent lines (using only spaces).
    new_indent = " " * len(orig_indent)
    
    # Remove the original indent from the content.
    content = line[len(orig_indent):]
    
    # If the whole line is already within the limit, return it as-is.
    if len(line) <= limit:
        return line

    # Calculate available width for content on each line.
    available_width = limit - len(orig_indent)
    wrapped_parts = textwrap.wrap(content, width=available_width)
    
    if not wrapped_parts:
        return line  # Fallback, though this is unlikely.
    
    # Reconstruct the wrapped text:
    # - Use the original indent on the first line (unchanged).
    # - For subsequent lines, prepend new_indent.
    wrapped_lines = []
    wrapped_lines.append(orig_indent + wrapped_parts[0])
    for part in wrapped_parts[1:]:
        wrapped_lines.append(new_indent + part)
    
    return "\n".join(wrapped_lines)

def wrap_full_text(text, limit):
    """
    Process the full text line-by-line. Each non-empty line is wrapped individually,
    preserving its original indent for the first line and applying a space-based indent
    for any wrapped lines.
    """
    lines = text.splitlines()
    wrapped_lines = [wrap_line(line, limit) for line in lines]
    return "\n".join(wrapped_lines)

def markdown_to_text(md_text):
    """
    Convert Markdown formatted text to plain text by removing common Markdown elements.
    """
    # Remove code block fences (``` ... ```)
    md_text = re.sub(r'```.*?```', lambda m: m.group(0).strip('`'), md_text, flags=re.DOTALL)
    # Remove inline code backticks
    md_text = re.sub(r'`([^`]+)`', r'\1', md_text)
    # Remove Markdown heading markers (#, ##, etc.) at the start of lines
    md_text = re.sub(r'^#+\s*', '', md_text, flags=re.MULTILINE)
    # Remove bold/italic markers (**text**, __text__, *text*, _text_)
    md_text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', md_text)
    md_text = re.sub(r'(\*|_)(.*?)\1', r'\2', md_text)
    # Replace links: [text](url) -> text
    md_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', md_text)
    # Replace images: ![alt](url) -> alt
    md_text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', md_text)
    # Remove horizontal rules (lines with 3 or more dashes or asterisks)
    md_text = re.sub(r'\n[-*]{3,}\n', '\n', md_text)
    # Remove blockquote markers ("> ")
    md_text = re.sub(r'^>\s?', '', md_text, flags=re.MULTILINE)
    
    # Optionally, remove extra spaces that might have been introduced.
    md_text = re.sub(r'[ ]{2,}', ' ', md_text)
    return md_text

if __name__ == "__main__":
    main()

