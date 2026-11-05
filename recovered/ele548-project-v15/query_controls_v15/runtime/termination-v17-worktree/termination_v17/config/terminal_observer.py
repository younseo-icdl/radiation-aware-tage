"""Bounded post-exit measurement observer; no predictor state mutation."""
def valid(s):
 assert s['conserved'] and s['applied_faults']==0,'INTEGRITY_FAILURE_NOT_CENSORED'
 assert s['early_claimed']==s['early_delivered']+s['early_pending'],'EARLY_OWNER_ACCOUNTING'
 assert s['lookup_accepted']==s['lookup_consumed']+s['lookup_cancelled']+s['lookup_pending'],'LOOKUP_ACCOUNTING'
 assert s['source_accepted']==s['source_completed']+s['source_cancelled']+s['source_pending'],'SOURCE_ACCOUNTING'
 assert s['lookups']==s['lookup_consumed']+s['early_pending'],'PREDICTION_CHECKPOINT_ACCOUNTING'
 assert s['ingress_enqueued']>=s['ingress_issued'],'INGRESS_ACCOUNTING'
def quiescent(s):
 return not(s['early_pending'] or s['lookup_pending'] or s['source_pending'] or s['ingress_enqueued']!=s['ingress_issued'])
def observe(initial,advance,sample,limit=64):
 valid(initial);s=initial;trace=[s]
 for step in range(limit+1):
  if quiescent(s):return trace
  assert step<limit,'UNRESOLVED_TERMINAL_REQUESTS_NOT_MASKED'
  advance();next_state=sample();valid(next_state)
  assert next_state['tick']-s['tick']==500 and next_state['source_cycles']-s['source_cycles']==1,'BAD_ACTUAL_CLOCK_PROGRESS'
  trace.append(next_state);s=next_state
 raise AssertionError('UNREACHABLE')
