from random import randrange, uniform
from time import time
from qiskit import *
from functions.my_module_QC import ibmq_load_account
from functions.quantum_algos import Shors_algo, two_qubit_algo, QFT, Grover, BV
from pprint import pprint

def view2_post_func(algo, trans_times, backend_name, query_data):


    # 每种 qubit 的T1，T2， error rate的平均值是多少
    backend_data = query_data['data'][backend_name] # list

    backend_qubit_avg = {
        'T1': {},
        'T2': {},
        'error_rate': {}
    }

    for date in backend_data:
        for i, d in enumerate(date['qubit']):
            if 'q_{}'.format(i) not in backend_qubit_avg['T1']:
                backend_qubit_avg['T1']['q_{}'.format(i)] = 0 # 看看有哪些qubit T1，并创建
            if 'q_{}'.format(i) not in backend_qubit_avg['T2']:
                backend_qubit_avg['T2']['q_{}'.format(i)] = 0 # 看看有哪些qubit T2，并创建
            if 'q_{}'.format(i) not in backend_qubit_avg['error_rate']:
                backend_qubit_avg['error_rate']['q_{}'.format(i)] = 0 # 看看有哪些qubit error_rate，并创建

    for attr in ['T1', 'T2', 'error_rate']:
        for qubit, _ in backend_qubit_avg[attr].items():
            i = int(qubit.split('_')[1])
            temp_arr = []
            for date in backend_data:
                temp_arr.append(date['qubit'][i][attr])
            backend_qubit_avg[attr][qubit] = cal_average(temp_arr)


    # backend_qubit_avg 里面装的是 该backend下 每个qubit 的T1, T2, error rate的平均值 （时间跨度取自 view1 数据）
    # print(backend_qubit_avg)


    # 每种 gate 的error rate的平均值是多少
    backend_gate_avg = {
        'error_rate': {}
    }

    for date in backend_data:
        for i, d in enumerate(date['gate']):
            if d['gate_name'] not in backend_gate_avg['error_rate']:
                backend_gate_avg['error_rate'][d['gate_name']] = 0 # 看看有哪些 gate，并创建

    for gate, _ in backend_gate_avg['error_rate'].items():
        temp_arr = []
        for date in backend_data:
            for _gate in date['gate']:
                if _gate['gate_name'] == gate:
                    temp_arr.append(_gate['error_rate'])
                    break
        backend_gate_avg['error_rate'][gate] = cal_average(temp_arr)

    # backend_gate_avg 里面装的是 该 backend下 每个 gate 的 error rate的平均值 （时间跨度取自 view1 数据）
    # print(backend_gate_avg)



    provider = ibmq_load_account()
    backend = provider.get_backend(backend_name)

    shot = 1000

    # build a quantum circuit

    # 根据传进来的 algo 名称，决定algo
    if algo == 'shor':
        qc = Shors_algo()
    elif algo == 'two_qubit':
        qc = two_qubit_algo()
    elif algo=='qft':
        qc = QFT()
    elif algo=='grover':
        qc = Grover()
    elif algo=='bv':
        qc = BV()
    else:
        qc = Shors_algo()





    # 用来存放 transpiled circuit 的 list, 最后 execute 用的 e.g., {'trans_1': qc.class}
    trans_data = {}
    circuit_data = {}


    for i in range(trans_times):
        qc_comp = transpile(qc, backend=backend)
        trans_data['trans_{}'.format(i)] = qc_comp._data
        circuit_data['trans_{}'.format(i)] = qc_comp






    # 用来生成画图用的数据
    data = {}

    # 开始构造 data
    for trans_name, qc in trans_data.items():



        # 每种qubit被用了多少次
        # 每种 gate 被用了多少次
        # pprint(qc)

        qubit_count = {}
        gate_count = {}

        for inst in qc:
            if inst[0].name == 'cx': # 先暂时只考虑 cx gate
                q_src = inst[1][0].index
                q_tgt = inst[1][1].index
                gate = 'cx{}_{}'.format(q_src, q_tgt)

                # 判断 q_src 在不在qubit_count 里
                if q_src not in qubit_count:
                    qubit_count[q_src] = 1
                else:
                    qubit_count[q_src] += 1

                # 判断 q_tgt 在不在qubit_count 里
                if q_tgt not in qubit_count:
                    qubit_count[q_tgt] = 1
                else:
                    qubit_count[q_tgt] += 1


                # # 判断 gate 在不在 gate_count 里
                if gate in gate_count :
                    gate_count[gate] += 1
                elif 'cx{}_{}'.format(q_tgt, q_src) in gate_count:
                    gate_count['cx{}_{}'.format(q_tgt, q_src)] += 1
                else:
                    gate_count[gate] = 1


        # print(backend_qubit_avg)
        # print(backend_gate_avg)
        # print(qubit_count)
        # print(gate_count)

        # 准备好 均值 和 次数，开始构造 qubit 数组
        q = {}
        for name, times in qubit_count.items():
            name = 'q_{}'.format(name)
            q[name] = {
                'times': times,
                'T1': backend_qubit_avg['T1'][name],
                'T2': backend_qubit_avg['T2'][name],
                'error_rate': backend_qubit_avg['error_rate'][name],
            }

        # 准备好 均值 和 次数，开始构造 gate 数组
        g = {}
        for name, times in gate_count.items():
            source = name[2]
            target = name[4]
            error_rate = 0
            if 'cx{}_{}'.format(source, target) in backend_gate_avg['error_rate']:
                error_rate = backend_gate_avg['error_rate']['cx{}_{}'.format(source, target)]
            elif 'cx{}_{}'.format(target, source) in backend_gate_avg['error_rate']:
                error_rate = backend_gate_avg['error_rate']['cx{}_{}'.format(target, source)]
            g[name] = {
                'times': times,
                'source': 'q_{}'.format(source),
                'target': 'q_{}'.format(target),
                'error_rate': error_rate
            }



        trans = {}

        trans['id'] = trans_name
        trans['depth'] = len(qc)
        trans['qubits_quality'] = cal_overall_qubit_quality(q)
        trans['gates_quality'] = cal_overall_gate_quality(g)
        trans['qubits'] = q
        trans['gates'] = g

        data[trans_name] = trans

    # pprint(data)

    # 开始构造 ref_value ，用来计算每个transpile circuit的qubit quality和gate quality的均值
    ref_value = {}

    qubit_qual_arr = []
    gate_qual_arr = []

    for _, trans in data.items():
        qubit_qual_arr.append(trans['qubits_quality'])
        gate_qual_arr.append(trans['gates_quality'])

    ref_value['qubit_qual_avg'] = cal_average(qubit_qual_arr)
    ref_value['gate_qual_avg'] = cal_average(gate_qual_arr)


    # 开始计算每一个 qubit, gate 在所有compiled circuit中的平均使用次数
    qubit_times_arr = {}
    gate_times_arr = {}

    for _, trans in data.items():
        # qubit
        for qname, qubit in trans['qubits'].items():
            if qname not in qubit_times_arr:
                qubit_times_arr[qname] = []
                qubit_times_arr[qname].append(qubit['times'])
            else:
                qubit_times_arr[qname].append(qubit['times'])
        # gate
        for gname, gate in trans['gates'].items():
            src = int(gname[2])
            tgt = int(gname[4])

            if gname in gate_times_arr:
                gate_times_arr[gname].append(gate['times'])
            elif 'cx{}_{}'.format(tgt, src) in gate_times_arr:
                gate_times_arr['cx{}_{}'.format(tgt, src)].append(gate['times'])
            else:
                gate_times_arr[gname] = []
                gate_times_arr[gname].append(gate['times'])

    # 根据 gname 求平均数
    for gname, arr in gate_times_arr.items():
        gate_times_arr[gname] = cal_average(arr)

    # 根据 qname 求平均数
    for qname, arr in qubit_times_arr.items():
        qubit_times_arr[qname] = cal_average(arr)

    ref_value['qubit_times_avg'] = qubit_times_arr
    ref_value['gate_times_avg'] = gate_times_arr



    # 左边返回的是用来响应 POST 请求的数据 画图用的， 右边的是编译得到的 circuit 数组, 最后 execute 用的
    return [data, circuit_data, ref_value]
    # return data




# 内部函数，用来计算一个数组的均值
def cal_average(num):
    sum_num = 0
    for t in num:
        sum_num = sum_num + t

    avg = sum_num / len(num)
    return round(avg, 6)


# 内部函数，计算一个 circuit 的 overall qubit quality
def cal_overall_qubit_quality(q):
    num = 0
    summary = []
    for _, qubit in q.items():
        num += qubit['times']
        summary.append(qubit['error_rate'] * qubit['times'])

    overall_qubit_qual = 1/(sum(summary)/num)

    return overall_qubit_qual

# 内部函数，计算一个 circuit 的 overall gate quality
def cal_overall_gate_quality(g):
    num = 0
    summary = []
    for _, gate in g.items():
        num += gate['times']
        summary.append(gate['error_rate'] * gate['times'])

    overall_gate_qual = 1/(sum(summary)/num)

    return overall_gate_qual

