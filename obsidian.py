#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Obsidian笔记库扫描服务"""

import os
import json
from datetime import datetime
from pathlib import Path

OBSIDIAN_ROOT = os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents")

def get_folders():
    """获取笔记库目录结构"""
    folders = []
    for item in sorted(os.listdir(OBSIDIAN_ROOT)):
        full_path = os.path.join(OBSIDIAN_ROOT, item)
        if os.path.isdir(full_path) and not item.startswith('.'):
            # 统计笔记数量
            md_count = len([f for f in os.listdir(full_path) if f.endswith('.md') and not f.startswith('.')])
            folders.append({
                'name': item,
                'path': item,
                'note_count': md_count
            })
    return folders


def get_notes(folder=None, page=1, per_page=20, search=None):
    """获取笔记列表"""
    if folder:
        base_path = os.path.join(OBSIDIAN_ROOT, folder)
    else:
        base_path = OBSIDIAN_ROOT
    
    if not os.path.exists(base_path):
        return {'notes': [], 'total': 0, 'page': page, 'per_page': per_page}
    
    notes = []
    
    if folder:
        # 获取单个文件夹下的笔记
        for f in os.listdir(base_path):
            if f.endswith('.md') and not f.startswith('.'):
                file_path = os.path.join(base_path, f)
                stat = os.stat(file_path)
                
                # 读取标题（第一行）
                title = f.replace('.md', '')
                try:
                    with open(file_path, 'r', encoding='utf-8') as fh:
                        first_line = fh.readline().strip()
                        if first_line.startswith('# '):
                            title = first_line[2:]
                except:
                    pass
                
                # 搜索过滤
                if search and search.lower() not in title.lower() and search.lower() not in f.lower():
                    continue
                
                notes.append({
                    'title': title,
                    'filename': f,
                    'folder': folder,
                    'path': f"{folder}/{f}",
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
    else:
        # 递归获取所有笔记（限制深度2层）
        for root, dirs, files in os.walk(base_path):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            # 计算相对路径
            rel_path = os.path.relpath(root, OBSIDIAN_ROOT)
            if rel_path == '.':
                rel_path = ''
            
            # 限制深度
            depth = len(rel_path.split(os.sep)) if rel_path else 0
            if depth > 2:
                continue
            
            for f in files:
                if f.endswith('.md') and not f.startswith('.'):
                    file_path = os.path.join(root, f)
                    stat = os.stat(file_path)
                    
                    title = f.replace('.md', '')
                    try:
                        with open(file_path, 'r', encoding='utf-8') as fh:
                            first_line = fh.readline().strip()
                            if first_line.startswith('# '):
                                title = first_line[2:]
                    except:
                        pass
                    
                    if search and search.lower() not in title.lower() and search.lower() not in f.lower():
                        continue
                    
                    folder_name = rel_path.split(os.sep)[0] if rel_path else '根目录'
                    
                    notes.append({
                        'title': title,
                        'filename': f,
                        'folder': folder_name,
                        'path': f"{rel_path}/{f}" if rel_path else f,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })
    
    # 按修改时间排序
    notes.sort(key=lambda x: x['modified'], reverse=True)
    
    total = len(notes)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'notes': notes[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }


def get_note_content(path):
    """获取笔记内容"""
    file_path = os.path.join(OBSIDIAN_ROOT, path)
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        stat = os.stat(file_path)
        
        return {
            'path': path,
            'content': content,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    except Exception as e:
        return {'error': str(e)}


def search_notes(query, limit=50):
    """全文搜索笔记"""
    results = []
    query_lower = query.lower()
    
    for root, dirs, files in os.walk(OBSIDIAN_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        rel_path = os.path.relpath(root, OBSIDIAN_ROOT)
        depth = len(rel_path.split(os.sep)) if rel_path != '.' else 0
        if depth > 3:
            continue
        
        for f in files:
            if f.endswith('.md') and not f.startswith('.'):
                file_path = os.path.join(root, f)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    
                    if query_lower in content.lower() or query_lower in f.lower():
                        title = f.replace('.md', '')
                        lines = content.split('\n')
                        if lines and lines[0].startswith('# '):
                            title = lines[0][2:]
                        
                        # 找到匹配的上下文
                        context = ''
                        for line in lines:
                            if query_lower in line.lower():
                                context = line.strip()[:200]
                                break
                        
                        folder_name = rel_path.split(os.sep)[0] if rel_path != '.' else '根目录'
                        
                        results.append({
                            'title': title,
                            'filename': f,
                            'folder': folder_name,
                            'path': os.path.relpath(file_path, OBSIDIAN_ROOT),
                            'context': context,
                            'size': os.path.getsize(file_path)
                        })
                        
                        if len(results) >= limit:
                            return results
                except:
                    continue
    
    return results
