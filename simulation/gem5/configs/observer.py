"""Actual post-exit helper completion; exposure and performance stay frozen."""
def valid(s):
 assert s['conserved'] and s['faults_frozen'],'INTEGRITY_OR_CENSOR_FAILURE'
 assert s['early_claimed']==s['early_delivered']+s['early_pending'],'EARLY_ACCOUNTING'
 assert s['lookup_accepted']==s['lookup_consumed']+s['lookup_cancelled']+s['lookup_pending'],'LOOKUP_ACCOUNTING'
 assert s['source_accepted']==s['source_completed']+s['source_cancelled']+s['source_pending'],'SOURCE_ACCOUNTING'
 assert s['lookups']==s['lookup_consumed']+s['early_pending'],'PREDICTION_CHECKPOINT_ACCOUNTING'
 assert s['ingress_enqueued']>=s['ingress_issued'],'INGRESS_ACCOUNTING'
 assert s['applied_events']+s['future_events_censored']==s['scheduled_events'],'EVENT_CENSOR_ACCOUNTING'
def idle(s):
 return not(s['early_pending'] or s['lookup_pending'] or s['source_pending'] or s['ingress_enqueued']!=s['ingress_issued']) and s['protection_pipeline_drained']
def observe(initial,advance,sample,limit=64):
 valid(initial);s=initial;trace=[s]
 fixed=('applied_events','applied_flips','censor_tick','scheduled_events','future_events_censored','committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash')
 for step in range(limit+1):
  if idle(s):return trace
  assert step<limit,'UNRESOLVED_HELPER_NOT_MASKED'
  advance();n=sample();valid(n)
  assert n['tick']-s['tick']==500 and n['source_cycles']-s['source_cycles']==1,'BAD_CLOCK_PROGRESS'
  assert all(n[k]==initial[k] for k in fixed),'EXPOSURE_OR_ARCHITECTURE_EXTENDED_AFTER_EXIT'
  trace.append(n);s=n
 raise AssertionError('UNREACHABLE')
