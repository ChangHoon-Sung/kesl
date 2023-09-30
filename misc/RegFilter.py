import os
import asyncio
from tqdm.asyncio import tqdm_asyncio
import subprocess
from collections import defaultdict

def replace_special_chars(string):
    # define a list of special characters
    special_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

    # replace each special character with an underbar
    for char in special_chars:
        string = string.replace(char, '_')
    return string

async def process_log_line(line, progress_bar, stats, lock):
    # split the line into 4 columns and extract the file path and process name
    process_name, filepath = line.split()[-2:]

    # check if the file path exists and is a regular file, directory, or non-existent
    if os.path.exists(filepath):
        if os.path.isfile(filepath):

            # acquire the lock and update the stats dictionary for regular files
            async with lock:
                if process_name not in stats:
                    stats[process_name] = {'regular_files': 0, 'directories': 0, 'not_regular_or_directory': 0, 'non_existent_files': 0, 'regular_file_log': [], 'proc files': 0}
                
                if filepath.startswith('/proc'):
                    stats[process_name]['proc files'] += 1
                else:
                    stats[process_name]['regular_files'] += 1
                    stats[process_name]['regular_file_log'].append(line)

        elif os.path.isdir(filepath):
            # acquire the lock and update the stats dictionary for directories
            async with lock:
                if process_name not in stats:
                    stats[process_name] = {'regular_files': 0, 'directories': 0, 'not_regular_or_directory': 0, 'non_existent_files': 0, 'regular_file_log': [], 'proc files': 0}
                stats[process_name]['directories'] += 1
        else:
            # acquire the lock and update the stats dictionary for files that are not regular or directories
            async with lock:
                if process_name not in stats:
                    stats[process_name] = {'regular_files': 0, 'directories': 0, 'not_regular_or_directory': 0, 'non_existent_files': 0, 'regular_file_log': [], 'proc files': 0}
                stats[process_name]['not_regular_or_directory'] += 1
    else:
        # acquire the lock and update the stats dictionary for non-existent files
        async with lock:
            if process_name not in stats:
                stats[process_name] = {'regular_files': 0, 'directories': 0, 'not_regular_or_directory': 0, 'non_existent_files': 0, 'regular_file_log': [], 'proc files': 0}
            stats[process_name]['non_existent_files'] += 1
    # update the progress bar
    progress_bar.update()


async def main(trace_filepath):

    # read the log file
    with open(trace_filepath, "r") as f:
        # create a progress bar with the total number of lines in the log file
        output = subprocess.check_output(['wc', '-l', trace_filepath])
        line_count = int(output.decode().split()[0])
        progress_bar = tqdm_asyncio(total=line_count, desc="Processing log file")

        # initialize a dictionary to store the stats and a lock to protect it
        stats = {}
        lock = asyncio.Lock()

        # create a list of tasks for each line of the log file
        tasks = [process_log_line(line, progress_bar, stats, lock) for line in f]

        # wait for the tasks to complete
        await asyncio.gather(*tasks)

        # close the progress bar
        progress_bar.close()

        # print the stats for each process name, including the counts for regular files, directories, files that are not regular or directories, and non-existent files
        for process_name, counts in sorted(stats.items(), key=lambda item: item[1].get('regular_files', 0)):
            print(process_name, counts.get('regular_files', 0), counts.get('directories', 0), counts.get('not_regular_or_directory', 0), counts.get('non_existent_files', 0))
            
            # save the regular file paths for the current process to a file in the 'regular_files_per_process' folder
            if not os.path.exists('regular_files_per_process'):
                os.mkdir('regular_files_per_process')
            
            process_path = os.path.join('regular_files_per_process', f'{replace_special_chars(process_name)}.log')
            if counts.get('regular_files', 0) > 0:
                with open(process_path, "w") as f:
                    for line in counts.get('regular_file_log'):
                        f.write(f"{line}")
        
        # calculate the total counts for all process names
        total_counts = defaultdict(int)
        for process_name, counts in stats.items():
            for file_type, count in counts.items():
                if file_type == 'regular_file_log':
                    continue
                total_counts[file_type] += count
        
        # print the statistics
        print("Total regular files:", total_counts.get('regular_files', 0))
        print("Total directories:", total_counts.get('directories', 0))
        print("Total proc files:", total_counts.get('proc files', 0))
        print("Total not regular or directory:", total_counts.get('not_regular_or_directory', 0))
        print("Total non-existent files:", total_counts.get('non_existent_files', 0))
        print("Total all file types:", sum(total_counts.values()))


if __name__ == "__main__":
    asyncio.run(main("traces/bpftrace-open.out"))
