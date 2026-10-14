"""Transactional source health, incident revisions, review and local outbox."""
import hashlib
import json
import re
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
        CREATE TABLE IF NOT EXISTS review_decisions(
          id INTEGER PRIMARY KEY, incident TEXT NOT NULL, revision INTEGER NOT NULL,
          decision TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL,
          at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS subscriptions(
          id TEXT PRIMARY KEY, areas TEXT NOT NULL, categories TEXT NOT NULL,
          enabled INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox(
          id TEXT PRIMARY KEY, subscription TEXT NOT NULL, incident TEXT NOT NULL,
          revision INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
          created TEXT NOT NULL, acknowledged TEXT, UNIQUE(subscription,incident,revision));
        CREATE TABLE IF NOT EXISTS lifecycle(
          incident TEXT PRIMARY KEY, effective_status TEXT NOT NULL,
          changed TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS duplicate_candidates(
          first_incident TEXT NOT NULL, second_incident TEXT NOT NULL,
          detected TEXT NOT NULL, reason TEXT NOT NULL,
          state TEXT NOT NULL DEFAULT 'candidate',
          PRIMARY KEY(first_incident,second_incident),
          CHECK(first_incident < second_incident));
        ''')

        # Additive migration preserves existing incidents and history.
        columns = {r['name'] for r in self.db.execute('PRAGMA table_info(sources)')}
        if 'published' not in columns:
            self.db.execute('ALTER TABLE sources ADD COLUMN published TEXT')
            self.db.commit()

    def audit(self, action, subject, actor, detail, now):
        self.db.execute('INSERT INTO audit(at,action,subject,actor,detail) VALUES(?,?,?,?,?)',
                        (now, action, subject, actor, canonical(detail)))

    @staticmethod
    def _title_tokens(value):
        return {token for token in re.findall(r'[a-z0-9]+', value.casefold()) if len(token) > 2}

    def _detect_duplicate_candidates(self, incident_id, now):
        self.db.execute("UPDATE duplicate_candidates SET state='candidate' WHERE first_incident=? OR second_incident=?",
                        (incident_id, incident_id))
        current = self.db.execute('SELECT * FROM incidents WHERE id=?', (incident_id,)).fetchone()
        if not current:
            return
        item = json.loads(current['data'])
        item_tokens = self._title_tokens(item['title'])
        for other in self.db.execute('SELECT * FROM incidents WHERE id<>?', (incident_id,)).fetchall():
            candidate = json.loads(other['data'])
            if candidate['category'] != item['category']:
                continue
            if not set(candidate['areas']) & set(item['areas']):
                continue
            seconds = abs((instant(candidate['issued']) - instant(item['issued'])).total_seconds())
            if seconds > 86400:
                continue
            other_tokens = self._title_tokens(candidate['title'])
            union = item_tokens | other_tokens
            similarity = len(item_tokens & other_tokens) / len(union) if union else 0
            if similarity < 0.5:
                continue
            first, second = sorted((incident_id, other['id']))
            reason = canonical({
                'area_overlap': sorted(set(candidate['areas']) & set(item['areas'])),
                'category': item['category'],
                'issued_within_hours': round(seconds / 3600, 2),
                'title_token_similarity': round(similarity, 3),
            })
            cursor = self.db.execute(
                'INSERT OR IGNORE INTO duplicate_candidates(first_incident,second_incident,detected,reason) VALUES(?,?,?,?)',
                (first, second, now, reason))
            if cursor.rowcount:
                self.audit('duplicate_candidate_created', first + ':' + second,
                           'system', json.loads(reason), now)

    def refresh_lifecycle(self, now=None):
        """Record effective expiry without changing publisher-supplied incident status."""
        now = now or utc()
        current = instant(now)
        changed = 0
        with self.db:
            for row in self.db.execute('SELECT id,data FROM incidents').fetchall():
                record = json.loads(row['data'])
                effective = record['status']
                if (effective == 'active' and record['expires'] is not None
                        and instant(record['expires']) <= current):
                    effective = 'expired'
                old = self.db.execute(
                    'SELECT effective_status FROM lifecycle WHERE incident=?', (row['id'],)).fetchone()
                if old and old['effective_status'] == effective:
                    continue
                self.db.execute(
                    'INSERT INTO lifecycle(incident,effective_status,changed) VALUES(?,?,?) '
                    'ON CONFLICT(incident) DO UPDATE SET effective_status=excluded.effective_status,changed=excluded.changed',
                    (row['id'], effective, now))
                self.audit('lifecycle_changed', row['id'], 'system',
                           {'before': old['effective_status'] if old else None,
                            'after': effective,
                            'publisher_status': record['status']}, now)
                changed += 1
        return changed

    def duplicate_candidates(self, state='candidate'):
        rows = self.db.execute(
            'SELECT * FROM duplicate_candidates WHERE state=? ORDER BY detected,first_incident,second_incident',
            (state,)).fetchall()
        return [{**dict(row), 'reason': json.loads(row['reason'])} for row in rows]

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
                self._detect_duplicate_candidates(id, now)
                changed += 1
            self.db.execute('UPDATE sources SET checked=?,succeeded=?,failures=0,error=NULL,raw_hash=?,published=? WHERE id=?',
                            (now,now,raw_hash,published,source_id))
        # An item disappearing from a feed is NOT evidence of resolution.
        return changed

    def failure(self, source_id, error, now=None):
        with self.db:
            self.db.execute('UPDATE sources SET checked=?,failures=failures+1,error=? WHERE id=?',
                            (now or utc(),str(error)[:200],source_id))

    def review_queue(self):
        """Local operator inspection; not a public or authenticated endpoint."""
        return [dict(row, data=json.loads(row['data'])) for row in self.db.execute(
            "SELECT * FROM incidents WHERE review='pending' ORDER BY source,id")]

    def review_detail(self, id, revision):
        row = self.db.execute('SELECT * FROM incidents WHERE id=?', (id,)).fetchone()
        if not row or row['revision'] != revision:
            raise ValueError('Stale review: inspect the current revision')
        history = self.db.execute('SELECT * FROM history WHERE incident=? AND revision=?',
                                  (id, revision)).fetchone()
        return {'incident': dict(row, data=json.loads(row['data'])),
                'changes': json.loads(history['changes']),
                'decisions': [dict(r) for r in self.db.execute(
                    'SELECT * FROM review_decisions WHERE incident=? ORDER BY id', (id,))]}

    def review_duplicate(self, first, second, revisions, decision, actor, reason, now=None):
        """Record a manual assessment; never merge or approve incidents."""
        if decision not in ('duplicate', 'distinct') or not actor.strip() or not reason.strip():
            raise ValueError('Decision, actor and reason required')
        with self.db:
            candidate = self.db.execute(
                'SELECT * FROM duplicate_candidates WHERE first_incident=? AND second_incident=?',
                (first, second)).fetchone()
            if not candidate:
                raise ValueError('Unknown candidate pair')
            current = tuple(self.db.execute('SELECT revision FROM incidents WHERE id=?',
                                           (id,)).fetchone()['revision'] for id in (first, second))
            if current != tuple(revisions):
                raise ValueError('Stale candidate: inspect both current revisions')
            self.db.execute('UPDATE duplicate_candidates SET state=? WHERE first_incident=? AND second_incident=?',
                            (decision, first, second))
            self.audit('duplicate_review', first, actor.strip(),
                       {'second': second, 'revisions': list(current), 'decision': decision,
                        'reason': reason.strip()}, now or utc())

    def review(self, id, revision, decision, actor, now=None, reason=None):
        if decision not in ('approved','rejected') or not actor.strip():
            raise ValueError('Explicit decision and reviewer required')
        # Legacy callers remain supported but cannot imply a documented rationale.
        reason = 'Not supplied (legacy local caller)' if reason is None else reason.strip()
        if not reason:
            raise ValueError('Review reason must not be blank')
        with self.db:
            row = self.db.execute('SELECT revision FROM incidents WHERE id=?',(id,)).fetchone()
            if not row or row['revision'] != revision:
                raise ValueError('Stale review: inspect the current revision')
            self.db.execute('UPDATE incidents SET review=? WHERE id=?',(decision,id))
            if decision == 'rejected':
                self.db.execute("UPDATE outbox SET state='superseded' WHERE incident=? AND state='pending'",(id,))
            at = now or utc()
            self.db.execute('INSERT INTO review_decisions(incident,revision,decision,actor,reason,at) VALUES(?,?,?,?,?,?)',
                            (id, revision, decision, actor.strip(), reason, at))
            self.audit('review_'+decision,id,actor.strip(),{'revision':revision, 'reason':reason},at)

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
        self.refresh_lifecycle(now)
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
        timestamp = now or utc()
        self.refresh_lifecycle(timestamp)
        lifecycle = {r['incident']: dict(r) for r in self.db.execute('SELECT * FROM lifecycle')}
        return {'generated':timestamp,'sources':self.health(timestamp),
                'incidents':[{**dict(r),'data':json.loads(r['data'])} for r in self.db.execute('SELECT * FROM incidents')],
                'history':[{**dict(r),'data':json.loads(r['data']),'changes':json.loads(r['changes'])} for r in self.db.execute('SELECT * FROM history ORDER BY at,revision')],
                'outbox':[dict(r) for r in self.db.execute('SELECT * FROM outbox')],
                'lifecycle':lifecycle,
                'duplicate_candidates':self.duplicate_candidates()}

