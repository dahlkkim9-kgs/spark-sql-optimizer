# 测试子查询解析逻辑
content = '''LEFT JOIN (SELECT corp_inn_accno,curr_code,cdpt_accno FROM rbdb.cdc_cpcddb_tb_cdmst_deppdcon_acc WHERE start_dt <= '{DATA_DT}' AND end_dt > '{DATA_DT}' AND (cdpt_accno LIKE 'FTE%' OR cdpt_accno LIKE 'FTN%') ) t8 ON'''

i = 12  # 跳过 'LEFT JOIN '
if content[i] == '(':
    depth = 1
    in_string = False
    str_char = None
    i += 1
    subquery_start = i

    print(f'Start parsing at i={subquery_start}')

    iteration = 0
    while i < len(content) and depth > 0:
        char = content[i]

        prev_char = content[i-1] if i > subquery_start else ''
        is_escape = (prev_char == '\\')  # 修改转义字符检查

        if char in ("'", '"') and (i == subquery_start or not is_escape):
            if not in_string:
                in_string = True
                str_char = char
                print(f'  [{i}] String start: {char}')
            elif char == str_char:
                in_string = False
                print(f'  [{i}] String end: {char}')

        if in_string:
            i += 1
            continue

        if char == '(':
            depth += 1
            print(f'  [{i}] Open paren, depth={depth}')
        elif char == ')':
            depth -= 1
            print(f'  [{i}] Close paren, depth={depth}')

        i += 1
        iteration += 1
        if iteration > 300:
            print('  ... stopped after 300 iterations')
            break

    print(f'End: i={i}, depth={depth}')
    subquery = '(' + content[subquery_start:i-1] + ')'
    print(f'Subquery length: {len(subquery)}')
    print(f'Subquery: {subquery[:150]}...')
