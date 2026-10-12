"""Transactional source health, incident revisions, review and local outbox."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from .registry import validate_config


def utc():
    return datetime.now(timezone.utc).isoformat()


def instant(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be text')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Monitor:
    def __init__(self, path='eirewatch.sqlite'):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS sources(
          id TEXT PRIMARY KEY, config TEXT NOT NULL, checked TEXT, succeeded TEXT,
          failures INTEGER NOT NULL DEFAULT 0, error TEXT, raw_hash TEXT);
        CREATE TABLE IF NOT EXISTS incidents(
          id TEXT PRIMARY KEY, source TEXT NOT NULL REFERENCES sources(id),
          external_id TEXT NOT NULL, revision INTEGER NOT NULL, fingerprint TEXT NOT NULL,
          data TEXT NOT NULL, review TEXT NOT NULL, UNIQUE(source,external_id));
        CREATE TABLE IF NOT EXISTS history(
          incident TEXT NOT NULL, revision INTEGER NOT NULL, at TEXT NOT NULL,
          data TEXT NOT NULL, changes TEXT NOT NULL, PRIMARY KEY(incident,revision));
        CREATE TABLE IF NOT EXISTS audit(
          id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL,
          subject TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS subscriptions(
          id TEXT PRIMARY KEY, areas TEXT NOT NULL, categories TEXT NOT NULL,
          enabled INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox(
          id TEXT PRIMARY KEY, subscription TEXT NOT NULL, incident TEXT NOT NULL,
          revision INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
          created TEXT NOT NULL, acknowledged TEXT, UNIQUE(subscription,incident,revision));
        ''')

        # Additive migration preserves existing incidents and history.
        columns = {r['name'] for r in self.db.execute('PRAGMA table_info(sources)')}
        if 'published' not in columns:
            self.db.execute('ALTER TABLE sources ADD COLUMN published TEXT')
            self.db.commit()

    def audit(self, action, subject, actor, detail, now):
        self.db.execute('INSERT INTO audit(at,action,subject,actor,detail) VALUES(?,?,?,?,?)',
                        (now, action, subject, actor, canonical(detail)))

    def register(self, config):
        validate_config(config)
        with self.db:
            self.db.execute('INSERT INTO sources(id,config) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET config=excluded.config',
                            (config['id'], canonical(config)))

    def subscribe(self, id, areas, categories, enabled=True):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO subscriptions VALUES(?,?,?,?)',
                            (id, canonical(areas), canonical(categories), int(enabled)))

    @staticmethod
    def validate(record):
        required = {'id','title','category','areas','issued','updated','expires','status','url','instruction'}
        if not required <= record.keys():
            raise ValueError('Missing incident fields')
        for key in ('id','title','category','url','instruction'):
            if not isinstance(record[key], str) or len(record[key]) > 10000:
                raise ValueError('Invalid text field')
        if not record['id'] or not record['title']:
            raise ValueError('Empty incident identity')
        if not record['url'].startswith('https://'):
            raise ValueError('HTTPS source link required')
        if record['status'] not in ('active','resolved','withdrawn'):
            raise ValueError('Unknown incident state')
        if not isinstance(record['areas'], list) or not all(isinstance(a,str) for a in record['areas']):
            raise ValueError('Areas must be a list of strings')
        issued, updated = instant(record['issued']), instant(record['updated'])
        if updated < issued:
            raise ValueError('Update precedes issue')
        if record['expires'] is not None and instant(record['expires']) <= issued:
            raise ValueError('Expiry must follow issue')

    def ingest(self, source_id, records, now=None, raw_hash=None, published=None):
        now = now or utc()
        instant(now)
        source = self.db.execute('SELECT * FROM sources WHERE id=?',(source_id,)).fetchone()
        if not source:
            raise ValueError('Unknown source')
        config = json.loads(source['config'])
        if not config['approved_for_ingestion']:
            raise ValueError('Source ingestion is disabled pending approval')
        validate_config(config)
        if published is not None:
            if instant(published) > instant(now):
                raise ValueError('Publication timestamp is in the future')
            if source['published'] and instant(published) < instant(source['published']):
                raise ValueError('Publication timestamp regressed')
        # Validate the complete batch before committing any part of it.
        seen = set()
        for r in records:
            self.validate(r)
            if r['id'] in seen:
                raise ValueError('Duplicate source identity in batch')
            seen.add(r['id'])
        changed = 0
        with self.db:
            for r in records:
                id = digest([source_id,r['id']])
                old = self.db.execute('SELECT * FROM incidents WHERE id=?',(id,)).fetchone()
                fingerprint = digest(r)
                if old and old['fingerprint'] == fingerprint:
                    continue
                previous = json.loads(old['data']) if old else {}
                if old and instant(r['updated']) < instant(previous['updated']):
                    self.audit('older_revision_ignored',id,'collector',{},now)
                    continue
                revision = old['revision']+1 if old else 1
                changes = {k:{'before':previous.get(k),'after':v} for k,v in r.items() if previous.get(k)!=v}
                self.db.execute('INSERT INTO incidents VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,fingerprint=excluded.fingerprint,data=excluded.data,review=excluded.review',
                                (id,source_id,r['id'],revision,fingerprint,canonical(r),'pending'))
                self.db.execute('INSERT INTO history VALUES(?,?,?,?,?)',(id,revision,now,canonical(r),canonical(changes)))
                # Superseded notifications are never delivered as current information.
                self.db.execute("UPDATE outbox SET state='superseded' WHERE incident=? AND state='pending'",(id,))
                self.audit('revision_created',id,'collector',{'revision':revision},now)
                changed += 1
            self.db.execute('UPDATE sources SET checked=?,succeeded=?,failures=0,error=NULL,raw_hash=?,published=? WHERE id=?',
                            (now,now,raw_hash,published,source_id))
        # An item disappearing from a feed is NOT evidence of resolution.
        return changed

    def failure(self, source_id, error, now=None):
        with self.db:
            self.db.execute('UPDATE sources SET checked=?,failures=failures+1,error=? WHERE id=?',
                            (now or utc(),str(error)[:200],source_id))

    def review(self, id, revision, decision, actor, now=None):
        if decision not in ('approved','rejected') or not actor.strip():
            raise ValueError('Explicit decision and reviewer required')
        with self.db:
            row = self.db.execute('SELECT revision FROM incidents WHERE id=?',(id,)).fetchone()
            if not row or row['revision'] != revision:
                raise ValueError('Stale review: inspect the current revision')
            self.db.execute('UPDATE incidents SET review=? WHERE id=?',(decision,id))
            if decision == 'rejected':
                self.db.execute("UPDATE outbox SET state='superseded' WHERE incident=? AND state='pending'",(id,))
            self.audit('review_'+decision,id,actor,{'revision':revision},now or utc())

    def health(self, now=None):
        current = instant(now or utc())
        result = []
        for row in self.db.execute('SELECT * FROM sources ORDER BY id'):
            item = dict(row); config = json.loads(item.pop('config'))
            if not config['approved_for_ingestion']: status='disabled'
            elif item['failures']: status='unavailable'
            elif not item['succeeded']: status='never_checked'
            elif (current-instant(item['succeeded'])).total_seconds() > config['max_age_hours']*3600: status='stale'
            else: status='healthy'
            connection_status = status
            threshold = config.get('publication_max_age_hours')
            publication_status = 'not_configured'
            if threshold is not None:
                publication_status = 'unknown'
                if item['published']:
                    age = (current-instant(item['published'])).total_seconds()
                    publication_status = 'future' if age < 0 else ('stale' if age > threshold*3600 else 'fresh')
                if status == 'healthy' and publication_status != 'fresh':
                    status = 'publication_' + publication_status
            try:
                validate_config(config)
            except (ValueError, TypeError):
                status = 'configuration_invalid'
            item.update(status=status, connection_status=connection_status,
                        publication_status=publication_status, config=config)
            result.append(item)
        return result

    def queue(self, now=None):
        now=now or utc(); current=instant(now); added=0
        health={r['id']:r for r in self.health(now)}
        with self.db:
            for row in self.db.execute("SELECT * FROM incidents WHERE review='approved'").fetchall():
                r=json.loads(row['data']); source=health[row['source']]
                if source['status']!='healthy' or not source['config']['official'] or instant(r['issued'])>current:
                    continue
                active=r['status']=='active'
                if active and (not r['expires'] or instant(r['expires'])<=current):
                    continue
                for sub in self.db.execute('SELECT * FROM subscriptions WHERE enabled=1').fetchall():
                    previous=self.db.execute('SELECT 1 FROM outbox WHERE subscription=? AND incident=? AND revision<?',(sub['id'],row['id'],row['revision'])).fetchone()
                    matches=(not json.loads(sub['areas']) or bool(set(r['areas'])&set(json.loads(sub['areas'])))) and (not json.loads(sub['categories']) or r['category'] in json.loads(sub['categories']))
                    if active and not matches: continue
                    if not active and not previous: continue
                    key=digest([sub['id'],row['id'],row['revision']])
                    cur=self.db.execute('INSERT OR IGNORE INTO outbox(id,subscription,incident,revision,created) VALUES(?,?,?,?,?)',
                                        (key,sub['id'],row['id'],row['revision'],now))
                    added+=cur.rowcount
        return added

    def inbox(self, subscription, now=None):
        now=now or utc(); current=instant(now); health={r['id']:r for r in self.health(now)}
        rows=[]
        enabled=self.db.execute('SELECT enabled FROM subscriptions WHERE id=?',(subscription,)).fetchone()
        if not enabled or not enabled['enabled']: return rows
        for row in self.db.execute("SELECT o.*,i.data,i.source,i.review,i.revision AS current_revision FROM outbox o JOIN incidents i ON i.id=o.incident WHERE subscription=? AND state='pending'",(subscription,)):
            r=json.loads(row['data'])
            if row['review']!='approved' or row['revision']!=row['current_revision'] or health[row['source']]['status']!='healthy':continue
            if r['status']=='active' and (not r['expires'] or instant(r['expires'])<=current):continue
            rows.append({**dict(row),'data':r})
        return rows

    def acknowledge(self, id, subscription, now=None):
        with self.db:
            cursor=self.db.execute("UPDATE outbox SET state='acknowledged',acknowledged=? WHERE id=? AND subscription=? AND state='pending'",(now or utc(),id,subscription))
            if cursor.rowcount!=1: raise ValueError('Unknown or non-pending notification')
            self.audit('acknowledged',id,subscription,{},now or utc())

    def snapshot(self, now=None):
        return {'generated':now or utc(),'sources':self.health(now),
                'incidents':[{**dict(r),'data':json.loads(r['data'])} for r in self.db.execute('SELECT * FROM incidents')],
                'history':[{**dict(r),'data':json.loads(r['data']),'changes':json.loads(r['changes'])} for r in self.db.execute('SELECT * FROM history ORDER BY at,revision')],
                'outbox':[dict(r) for r in self.db.execute('SELECT * FROM outbox')]}
