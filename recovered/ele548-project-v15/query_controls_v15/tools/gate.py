#!/usr/bin/env python3
import argparse,sys
sys.dont_write_bytecode=True
import prepare as m
p=argparse.ArgumentParser();p.add_argument('test',choices=['query_gate','early_gate']);p.add_argument('--attempt',required=True);a=p.parse_args()
args=[m.BASE/'runtime'/('query_manifest_'+a.attempt+'.json')] if a.test=='query_gate' else []
m.gate(a.test,a.attempt,args)
