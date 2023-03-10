from datetime import datetime
import json
import os
from pathlib import Path

log_dir = Path("./traces")

process_hierarchy = {}
pid_index = {}

def update_process_hierarchy(log_file_path):
    count = 0
    with open(log_file_path, "r") as log_file:
        for line in log_file:
            try:
                count += 1
                print(count, end="\r")
                line = line.strip()
                date, time, pid, ppid, comm, path = line.split()
                path = Path(path)

                # if path is not a regular file, skip
                if not path.is_file() or any(path.is_relative_to(x) for x in ["/dev", "/proc", "/sys", "/run"]):
                    continue

                parent_process = pid_index.get(ppid)
                # 현재 프로세스의 부모 프로세스가 자료구조에 존재하는 경우
                if parent_process is not None:
                    if parent_process["ppid"] is None:
                        parent_process["ppid"] = ppid
                    
                    # 새로운 자식 프로세스인 경우
                    if pid in parent_process["children"].keys():
                        parent_process["children"][pid]["logs"].append(line)
                    else:
                        parent_process["children"][pid] = {
                            "ppid": ppid,
                            "comm": comm,
                            "logs": [line],
                            "children": {}
                        }
                        pid_index[pid] = parent_process["children"][pid]
                
                # 현재 프로세스의 부모 프로세스가 자료구조에 존재하지 않는 경우
                else:
                    # 최상단에 부모 확장
                    with open(f'/proc/{ppid}/comm', 'r') as f:
                        parent_comm = f.readline().strip()

                    parent_process = {
                        "ppid": None,           # 이 프로세스가 아직 추적된 적이 없음
                        "comm": parent_comm,
                        "logs": [],
                        "children": {}
                    }

                    process_hierarchy[ppid] = parent_process

                    # 현재 프로세스가 루트인 경우
                    if pid in process_hierarchy.keys():
                        process_hierarchy[pid]["logs"].append(line)
                    
                    # 현재 프로세스가 루트가 아닌 경우 (처음 발견)
                    else:
                        process_hierarchy[pid] = {
                            "ppid": ppid,
                            "comm": comm,
                            "logs": [line],
                            "children": {}
                        }

                    # 확장한 부모에 현재 프로세스를 자식으로 추가
                    process_hierarchy[ppid]["children"][pid] = process_hierarchy[pid]
                    pid_index[ppid] = process_hierarchy[ppid]
                    del process_hierarchy[pid]
            except Exception as e:
                print(line)
                print(count)
            
def get_process_hierarchy():
    for filename in os.listdir(log_dir):
        if filename.endswith(".log"):
            log_file_path = os.path.join(log_dir, filename)
            update_process_hierarchy(log_file_path)

    json.dump(process_hierarchy, open("traces/process_hierarchy.json", "w"))

def groupby_comm_per_level(process_hierarchy: None):
    if process_hierarchy is None:
        process_hierarchy = json.load(open("traces/process_hierarchy.json", "r"))

    comm_hierarchy = {}

    for pid, process in process_hierarchy.items():
        if comm_hierarchy.get(process["comm"]) is None:
            comm_hierarchy[process["comm"]] = {
                "comm": process["comm"],
                "logs": process["logs"],
                "children": {}
            }
        else:
            comm_hierarchy[process["comm"]]["logs"].extend(process["logs"])
            comm_hierarchy[process["comm"]]["logs"].sort(key=lambda x: datetime.strptime(f"{x.split()[0]} {x.split()[1]}",  "%Y-%m-%d %H:%M:%S:%f"))

        if len(process["children"]) > 0:
            comm_hierarchy[process["comm"]]["children"] = groupby_comm_per_level(process["children"])
    
    return comm_hierarchy


if __name__ == "__main__":
    
    get_process_hierarchy()
    # json.dump(groupby_comm_per_level(process_hierarchy), open("traces/comm_hierarchy.json", "w"))