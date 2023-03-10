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

                # 현재 프로세스의 부모 프로세스가 자료구조에 존재하는 경우
                parent_process = pid_index.get(ppid)
                if parent_process is not None:

                    # 현재 프로세스가 부모 프로세스에게 등록되어 있지 않은 경우
                    if pid not in parent_process["children"]:
                        process = {
                            "comm": comm,
                            "ppid": ppid,
                            "logs": [line],
                            "children": {}
                        }
                        parent_process["children"][pid] = process

                    # 현재 프로세스가 부모 프로세스에게 등록되어 있는 경우
                    else:
                        parent_process["children"][pid]["logs"].append(line)
                    
                    # 인덱스 등록
                    pid_index[pid] = parent_process["children"][pid]

                # 현재 프로세스의 부모 프로세스가 자료구조에 존재하지 않는 경우
                else:
                    # 현재 프로세스가 자료구조 최상위 계층에 존재하지 않는 경우
                    # 즉, 지금까지 발견된 프로세스보다 더 상위 계층의 프로세스가 발견된 경우
                    if pid not in process_hierarchy.keys():
                        process = {
                            "comm": comm,
                            "ppid": ppid,
                            "logs": [line],
                            "children": {}
                        }

                        # 자료구조 최상위 계층에서 현재 프로세스의 자식 프로세스를 찾아서 등록
                        child_pids = []
                        for child_cand_pid in process_hierarchy.keys():
                            if process_hierarchy[child_cand_pid]["ppid"] == pid:
                                child_pids.append(child_cand_pid)

                        for child_pid in child_pids:
                            process["children"][child_pid] = process_hierarchy[child_pid]
                            del process_hierarchy[child_pid]
                        
                        # 현재 프로세스를 자료구조 최상위 계층 및 인덱스에 등록
                        process_hierarchy[pid] = process
                        pid_index[pid] = process_hierarchy[pid]
                    
                    # 현재 프로세스가 자료구조 최상위 계층에 존재하는 경우
                    else:
                        current_process = process_hierarchy[pid]
                        current_process["logs"].append(line)
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
    json.dump(groupby_comm_per_level(process_hierarchy), open("traces/comm_hierarchy.json", "w"))