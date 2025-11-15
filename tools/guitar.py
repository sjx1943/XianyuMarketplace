#!/usr/bin/env python
# -*- coding: utf-8 -*-
#吉他 指弹练习指法生成

import random


def generate_random_numbers():
    numbers = set() #无重复元素集
    while len(numbers) < 6:
        if len(numbers) < 4:
            group = random.sample(range(1, 5), 4)
            random.shuffle(group)
        else:
            group = generate_group_with_repeated_numbers()
        numbers.add(tuple(group))
    return list(numbers)

def generate_group_with_repeated_numbers():
    group = []
    while len(group) < 4:
        num = random.randint(1, 4)
        if group.count(num) < 2:
            group.append(num)
    random.shuffle(group)
    return group

# 输出结果
groups = generate_random_numbers()
# print(groups)
for i in range(6):
    print(groups[i])
