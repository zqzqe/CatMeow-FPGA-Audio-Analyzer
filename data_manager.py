"""Immutable WAV library + transactional, reversible HUMAN annotations."""
from .bootstrap import ROOT
from .audio_engine import read_wav
from pathlib import Path
from datetime import datetime
import hashlib,json,csv,sqlite3,uuid,math,shutil

EVENTS=('cat_vocalization','non_cat','uncertain')
CONTEXTS=('B','F','I','unknown','not_applicable')
def now():return datetime.now().astimezone().isoformat(timespec='seconds')
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

class DataManager:
    def __init__(self,folder=None):
        self.root=Path(folder or ROOT/'data/library');self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'index.sqlite3');self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS recordings(
          id TEXT PRIMARY KEY,path TEXT NOT NULL,original_path TEXT,rate INTEGER,count INTEGER,
          source TEXT,created TEXT,cat_id TEXT DEFAULT '',owner_id TEXT DEFAULT '',
          room_id TEXT DEFAULT '',device_id TEXT DEFAULT '',session_json TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS annotations(
          id TEXT PRIMARY KEY,recording_id TEXT REFERENCES recordings(id),start REAL,end REAL,
          event TEXT,context TEXT,annotator TEXT,basis TEXT,context_verified INTEGER,
          created TEXT,updated TEXT,deleted INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS history(
          seq INTEGER PRIMARY KEY AUTOINCREMENT,recording_id TEXT,annotation_id TEXT,
          before_json TEXT,after_json TEXT,action TEXT,at TEXT,undone INTEGER DEFAULT 0);
        ''');self.db.commit()
    def close(self):self.db.close()
    def records(self):return [dict(r) for r in self.db.execute('SELECT * FROM recordings ORDER BY created DESC,id')]
    def get(self,rid):
        row=self.db.execute('SELECT * FROM recordings WHERE id=?',(rid,)).fetchone()
        if row is None:raise ValueError('未找到录音')
        return dict(row)
    def audio_path(self,rid):return self.root/self.get(rid)['path']
    def import_wav(self,path,source='user_import',session=None):
        path=Path(path).resolve();x,rate=read_wav(path)
        digest=sha256(path);target=self.root/(digest+'.wav')
        if target.exists():
            if sha256(target)!=digest:raise ValueError('库内文件哈希异常')
        else:
            with path.open('rb') as src,target.open('xb') as out:shutil.copyfileobj(src,out)
            if sha256(target)!=digest:raise ValueError('导入校验失败')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO recordings(id,path,original_path,rate,count,source,created,session_json) VALUES(?,?,?,?,?,?,?,?)',
                            (digest,target.name,str(path),rate,len(x),source,now(),json.dumps(session or {},ensure_ascii=False)))
            if session:
                old=json.loads(self.get(digest)['session_json'])
                entries=old.get('imports',[]) if 'imports' in old else ([old] if old else [])
                if session not in entries:entries.append(session)
                self.db.execute('UPDATE recordings SET session_json=? WHERE id=?',(json.dumps({'imports':entries},ensure_ascii=False),digest))
        # No guessed annotations, even when metadata/model happens to contain B/F/I.
        return digest
    def import_session(self,path):
        path=Path(path).resolve()
        if path.stat().st_size>4*1024*1024:raise ValueError('SESSION文件过大')
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict) or not isinstance(data.get('segments'),list) or not data['segments']:raise ValueError('SESSION必须包含segments列表')
        candidates=[]
        for segment in data['segments']:
            if not isinstance(segment,dict) or not isinstance(segment.get('file'),str):raise ValueError('SESSION段缺少WAV文件名')
            wav=(path.parent/segment['file']).resolve()
            if not wav.is_relative_to(path.parent) or wav.suffix.lower()!='.wav':raise ValueError('SESSION引用必须是同目录内WAV，禁止路径越界')
            x,rate=read_wav(wav)
            if ('count' in segment and segment['count']!=len(x)) or ('rate' in segment and segment['rate']!=rate):raise ValueError('SESSION声明的采样率/长度与WAV不一致')
            candidates.append(wav)
        return [self.import_wav(p,'session_import',dict(file=str(path),content=data)) for p in candidates]
    def update_ids(self,rid,cat_id='',owner_id='',room_id='',device_id=''):
        self.get(rid)
        with self.db:self.db.execute('UPDATE recordings SET cat_id=?,owner_id=?,room_id=?,device_id=? WHERE id=?',
                                    (cat_id.strip(),owner_id.strip(),room_id.strip(),device_id.strip(),rid))
    def annotations(self,rid):
        return [dict(r) for r in self.db.execute('SELECT * FROM annotations WHERE recording_id=? AND deleted=0 ORDER BY start,id',(rid,))]
    def _annotation(self,aid):
        r=self.db.execute('SELECT * FROM annotations WHERE id=?',(aid,)).fetchone();return dict(r) if r else None
    def save_annotation(self,rid,start,end,event,context,annotator,basis,context_verified=False,annotation_id=None):
        record=self.get(rid);start=float(start);end=float(end)
        if not math.isfinite(start+end) or not 0<=start<end<=record['count']/record['rate']+1e-9:raise ValueError('事件时间必须位于录音范围内且起点小于终点')
        if event not in EVENTS or context not in CONTEXTS:raise ValueError('未知标签')
        if not annotator.strip() or not basis.strip():raise ValueError('请填写标注人与依据')
        if context in ('B','F','I') and (event!='cat_vocalization' or not context_verified):raise ValueError('B/F/I必须有人工确认的真实情境依据，不能根据声音或模型猜测')
        if event=='non_cat' and context!='not_applicable':raise ValueError('non_cat的情境必须为not_applicable')
        if event=='uncertain' and context not in ('unknown','not_applicable'):raise ValueError('uncertain不能标注B/F/I')
        aid=annotation_id or uuid.uuid4().hex;before=self._annotation(aid)
        if annotation_id and (not before or before['recording_id']!=rid):raise ValueError('标注不属于该录音')
        after=dict(id=aid,recording_id=rid,start=start,end=end,event=event,context=context,annotator=annotator.strip(),basis=basis.strip(),
                   context_verified=int(context_verified),created=before['created'] if before else now(),updated=now(),deleted=0)
        self._commit_annotation(rid,aid,before,after,'modify' if before else 'create')
        return aid
    def _store(self,item):
        keys=list(item);self.db.execute(f"INSERT OR REPLACE INTO annotations({','.join(keys)}) VALUES({','.join('?' for _ in keys)})",list(item.values()))
    def _commit_annotation(self,rid,aid,before,after,action):
        with self.db:
            self._store(after)
            self.db.execute('INSERT INTO history(recording_id,annotation_id,before_json,after_json,action,at) VALUES(?,?,?,?,?,?)',
                            (rid,aid,json.dumps(before),json.dumps(after),action,now()))
    def delete_annotation(self,rid,aid):
        before=self._annotation(aid)
        if not before or before['recording_id']!=rid:raise ValueError('未找到该录音的标注')
        after={**before,'deleted':1,'updated':now()};self._commit_annotation(rid,aid,before,after,'delete')
    def undo(self,rid):
        row=self.db.execute('SELECT * FROM history WHERE recording_id=? AND undone=0 ORDER BY seq DESC LIMIT 1',(rid,)).fetchone()
        if not row:return False
        before=json.loads(row['before_json'])
        with self.db:
            if before is None:self.db.execute('DELETE FROM annotations WHERE id=?',(row['annotation_id'],))
            else:self._store(before)
            self.db.execute('UPDATE history SET undone=1 WHERE seq=?',(row['seq'],))
        return True
    def export(self,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        tag=datetime.now().strftime('%Y%m%d_%H%M%S_%f');base=folder/f'library_{tag}'
        records=self.records();annotations=[dict(r) for r in self.db.execute('SELECT * FROM annotations ORDER BY recording_id,start')]
        history=[dict(r) for r in self.db.execute('SELECT * FROM history ORDER BY seq')]
        index=base.with_suffix('.json')
        with index.open('x',encoding='utf-8') as f:json.dump(dict(schema=1,exported_at=now(),library_root=str(self.root.resolve()),recordings=records,annotations=annotations,history=history,
                   training_export=False,note='No automatic training ingestion. Events and contexts are separate HUMAN labels.'),f,ensure_ascii=False,indent=2)
        paths=[index]
        for name,rows in [('recordings',records),('annotations',annotations)]:
            out=base.with_name(base.name+'_'+name+'.csv')
            with out.open('x',newline='',encoding='utf-8-sig') as f:
                if rows:
                    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
                    for row in rows:
                        # Spreadsheet-safe text while JSON preserves literal values.
                        w.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
            paths.append(out)
        return paths
