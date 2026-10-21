"""Offline safety regression: all remote APIs, APK tools and uploads are fakes.

No git tag/release, signing secret, keystore or publication workflow is used.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import release_control as control

SHA = 'a'*40
VERSION = '0.1.0-alpha.1'
SIGNER = 'b'*64


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.responses = {
            '/branches/main':{'commit':{'sha':SHA},'protected':True},
            '/environments/moneymate-publication':{'protection_rules':[{'type':'required_reviewers','reviewers':[{'type':'User','reviewer':{'login':control.PO}}]}],'deployment_branch_policy':{'protected_branches':True}},
            '/pulls/42':{'merged':True,'merge_commit_sha':SHA,'base':{'ref':'main'},'head':{'ref':'release-candidates/initial'},'title':'chore(release): release '+VERSION,'labels':[{'name':'autorelease: pending'}]},
            '/pulls/42/files?per_page=100':[{'filename':'CHANGELOG.md'},{'filename':'.release-please-manifest.json'}],
            '/actions/workflows/ci.yml/runs?head_sha='+SHA+'&event=push&per_page=100':{'workflow_runs':[{'id':77,'head_sha':SHA,'event':'push','head_branch':'main','status':'completed','conclusion':'success'}]},
            '/actions/runs/77/jobs?per_page=100':{'jobs':[{'name':n,'conclusion':'success'} for n in ['Build, lint and test','Install and launch debug and R8 release APKs']]},
            '/git/ref/tags/v'+VERSION:None,
            '/releases/tags/v'+VERSION:None,
            '/releases?per_page=100':[], '/git/matching-refs/tags/':[],
            '/git/commits/'+SHA:{'tree':{'sha':'base-tree'}},
            '/labels/autorelease%3A%20pending':{'name':'autorelease: pending'},
        }
        self.responses['/environments/moneymate-candidate']=copy.deepcopy(self.responses['/environments/moneymate-publication'])

    def __call__(self, method, path, data=None, missing=False):
        self.calls.append((method,path,data))
        if method=='GET':
            if path.startswith('/git/ref/heads/release-candidates/'):
                return None
            return copy.deepcopy(self.responses[path])
        if path in ['/git/blobs','/git/trees','/git/commits']:
            return {'sha':'fake-object'}
        if path=='/pulls':
            return {'number':99}
        if path=='/git/tags':
            return {'sha':'annotation'}
        if path=='/git/refs' and data['ref'].startswith('refs/tags/'):
            self.responses['/git/ref/tags/v'+VERSION]={'object':{'type':'tag','sha':'annotation'}}
        if method=='POST' and path=='/releases':
            self.responses['/releases/9']={'assets':[{'name':'app-release.apk'},{'name':'app-release.apk.sha256'}]}
            return {'id':9}
        return {}


class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        # An accidental real network call makes any offline test fail.
        self.network=patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden in regression'))
        self.network.start();self.addCleanup(self.network.stop)
        self.api=FakeAPI()
        self.checksum=patch.object(control,'verify_checksum')
        self.checksum.start();self.addCleanup(self.checksum.stop)

    def test_publication_preflight_read_only_success(self):
        self.assertEqual(control.publication_preflight(self.api,SHA,VERSION,42,SIGNER),77)
        self.assertTrue(all(c[0]=='GET' for c in self.api.calls))

    def test_missing_controls_block_before_writes(self):
        cases=[
            ('main moved','/branches/main',{'commit':{'sha':'c'*40},'protected':True}),
            ('unprotected main','/branches/main',{'commit':{'sha':SHA},'protected':False}),
            ('no approval','/environments/moneymate-publication',{'protection_rules':[]}),
            ('unrestricted environment','/environments/moneymate-publication',{'protection_rules':[{'type':'required_reviewers','reviewers':[{'type':'User','reviewer':{'login':control.PO}}]}]}),
            ('extra product file','/pulls/42/files?per_page=100',[{'filename':'app/src/main/Bad.kt'}]),
            ('missing CI','/actions/workflows/ci.yml/runs?head_sha='+SHA+'&event=push&per_page=100',{'workflow_runs':[]}),
            ('newer failed CI','/actions/workflows/ci.yml/runs?head_sha='+SHA+'&event=push&per_page=100',{'workflow_runs':[{'id':77,'head_sha':SHA,'event':'push','head_branch':'main','status':'completed','conclusion':'success'},{'id':78,'head_sha':SHA,'event':'push','head_branch':'main','status':'completed','conclusion':'failure'}]}),
            ('missing job','/actions/runs/77/jobs?per_page=100',{'jobs':[]}),
            ('existing tag','/git/ref/tags/v'+VERSION,{'object':{'sha':'old'}}),
            ('existing release','/releases/tags/v'+VERSION,{'id':1}),
        ]
        for name,path,value in cases:
            with self.subTest(name=name):
                api=FakeAPI();api.responses[path]=value
                with self.assertRaises(ValueError):control.publication_preflight(api,SHA,VERSION,42,SIGNER)
                self.assertTrue(all(c[0]=='GET' for c in api.calls))

    def test_wrong_pr_and_wrong_fingerprint(self):
        for field,value in [('merged',False),('merge_commit_sha','c'*40),('title','ci(release): technical change'),('labels',[])]:
            with self.subTest(field=field):
                api=FakeAPI();api.responses['/pulls/42'][field]=value
                with self.assertRaises(ValueError):control.publication_preflight(api,SHA,VERSION,42,SIGNER)
        with self.assertRaises(ValueError):control.publication_preflight(self.api,SHA,VERSION,42,'invalid')

    def test_dispatch_intent_operator_and_attempt(self):
        good={'GITHUB_REPOSITORY':control.REPO,'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_ACTOR':control.PO,'GITHUB_TRIGGERING_ACTOR':control.PO,'GITHUB_RUN_ATTEMPT':'1','RELEASE_CONFIRMATION':'PUBLISH '+VERSION+' @ '+SHA}
        with patch.dict(os.environ,good,clear=True):control.dispatch_guard(VERSION,SHA,'PUBLISH')
        for key,value in [('GITHUB_REPOSITORY','other/repo'),('GITHUB_EVENT_NAME','push'),('GITHUB_REF','refs/heads/feature'),('GITHUB_ACTOR','other'),('GITHUB_TRIGGERING_ACTOR','other'),('GITHUB_RUN_ATTEMPT','2'),('RELEASE_CONFIRMATION','yes')]:
            with self.subTest(key=key),patch.dict(os.environ,{**good,key:value},clear=True):
                with self.assertRaises(ValueError):control.dispatch_guard(VERSION,SHA,'PUBLISH')

    def test_transport_write_boundaries(self):
        for mode,path,data in [('read','/git/tags',{}),('candidate','/git/tags',{}),('candidate','/releases',{}),('candidate','/pulls/42/merge',{}),('candidate','/git/refs',{'ref':'refs/tags/v'+VERSION}),('candidate','/git/refs',{'ref':'refs/heads/release-please--branches--main--components--MoneyMate'}),('publication','/pulls',{})]:
            with self.subTest(mode=mode,path=path),self.assertRaises(ValueError):control.API(mode,token='')( 'POST',path,data)

    def test_candidate_fresh_draft_only_and_labels(self):
        plan={'files':{n:'synthetic planning content' for n in control.FILES},'draft':True,'title':'chore(release): release '+VERSION,'version':VERSION,'versionCode':10001,'labels':['autorelease: pending']}
        self.assertEqual(control.create_candidate(self.api,plan,SHA),99)
        writes=[c for c in self.api.calls if c[0]!='GET']
        self.assertTrue(any(c[1]=='/issues/99/labels' for c in writes))
        self.assertTrue(next(c for c in writes if c[1]=='/pulls')[2]['draft'])
        self.assertFalse(any(c[1] in ['/git/tags','/releases'] for c in writes))
        self.assertTrue(all(c[2]['ref'].startswith('refs/heads/release-candidates/') for c in writes if c[1]=='/git/refs'))
        bad=copy.deepcopy(plan);bad['files']['README.md']='not allowed'
        with self.assertRaises(ValueError):control.create_candidate(FakeAPI(),bad,SHA)

    def test_candidate_stale_branch_never_overwritten(self):
        def api(method,path,data=None,missing=False):
            if path.startswith('/git/ref/heads/release-candidates/'):return {'object':{'sha':'existing'}}
            return self.api(method,path,data,missing)
        plan={'files':{n:'x' for n in control.FILES},'draft':True,'title':'chore(release): release '+VERSION,'version':VERSION,'labels':[]}
        with self.assertRaises(ValueError):control.create_candidate(api,plan,SHA)
        self.assertTrue(all(c[0]=='GET' for c in self.api.calls))

    def test_annotation_and_assets_order_only_on_fake_transport(self):
        with patch.object(control,'verify_local',return_value='Reviewed notes'),patch.object(control,'verify_apk'),patch.object(control.subprocess,'run') as upload:
            control.publish(self.api,SHA,VERSION,42,SIGNER,Path('app-release.apk'))
        writes=[c for c in self.api.calls if c[0]!='GET']
        self.assertEqual(writes[0][1],'/git/tags');self.assertEqual(writes[0][2]['type'],'commit');self.assertEqual(writes[0][2]['object'],SHA)
        self.assertEqual(writes[1][2]['ref'],'refs/tags/v'+VERSION)
        release=next(c for c in writes if c[1]=='/releases');self.assertTrue(release[2]['draft']);self.assertTrue(release[2]['prerelease'])
        self.assertIn('Implements Spec v2.1.0',release[2]['body']);self.assertEqual(writes[-1],('PATCH','/releases/9',{'draft':False}))
        upload.assert_called_once()

    def test_wrong_signer_blocks_all_publication_writes(self):
        with patch.object(control,'verify_local',return_value='notes'),patch.object(control.subprocess,'run'),patch.object(control.subprocess,'check_output',return_value='Signer #1 certificate SHA-256 digest: '+'c'*64+'\n'):
            with self.assertRaises(ValueError):control.publish(self.api,SHA,VERSION,42,SIGNER,Path('app-release.apk'))
        self.assertTrue(all(c[0]=='GET' for c in self.api.calls))

    def test_failed_upload_stays_draft_no_public_visibility(self):
        with patch.object(control,'verify_local',return_value='notes'),patch.object(control,'verify_apk'),patch.object(control.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'fake-upload')):
            with self.assertRaises(subprocess.CalledProcessError):control.publish(self.api,SHA,VERSION,42,SIGNER,Path('app-release.apk'))
        self.assertFalse(any(c[0]=='PATCH' for c in self.api.calls))

    def test_transferred_checksum_must_match_before_regeneration(self):
        self.checksum.stop()
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            apk=Path(directory)/'test.apk';apk.write_bytes(b'offline synthetic payload')
            checksum=Path(str(apk)+'.sha256')
            with self.assertRaises(ValueError):control.verify_checksum(apk)
            checksum.write_text(hashlib.sha256(apk.read_bytes()).hexdigest()+'  '+apk.name+'\n')
            control.verify_checksum(apk)
            apk.write_bytes(b'changed payload')
            with self.assertRaises(ValueError):control.verify_checksum(apk)

    def test_changelog_duplicate_pending_missing_sections_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);(p/'version.properties').write_text('VERSION_NAME='+VERSION+'\n');(p/'.release-please-manifest.json').write_text(json.dumps({'.':VERSION}))
            valid='# Changelog\n\n## [Unreleased]\n\n## ['+VERSION+'] - 2026-10-21\n'+''.join('### '+s+'\n' for s in ['Added','Changed','Fixed','Security','Breaking'])+'Spec: DOC-SPEC v2.1.0\n'
            with patch.object(control,'ROOT',p):
                (p/'CHANGELOG.md').write_text(valid);control.verify_local(VERSION)
                for bad in [valid+'## ['+VERSION+']\n',valid.replace('2026-10-21','Pending release'),valid.replace('### Security','### Other')]:
                    (p/'CHANGELOG.md').write_text(bad)
                    with self.assertRaises(ValueError):control.verify_local(VERSION)


if __name__=='__main__':
    unittest.main()
