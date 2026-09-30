const states = {
  review: 'Ready for research review',
  hold_for_evidence: 'Hold for evidence review',
  unavailable: 'Prediction unavailable',
  below_demo_threshold: 'Below the selected review threshold',
};

export function DecisionExplanation({ assessment }) {
  return <section className="panel mt-6" aria-labelledby="decision-explanation-title">
    <div className="panel-heading"><div><h2 id="decision-explanation-title">Why this decision?</h2><p>{states[assessment.status] ?? 'Research assessment'}</p></div><span className="small-tag">Public dispatch blocked</span></div>
    <dl className="evidence-list">
      <div><dt>Probability threshold</dt><dd>{assessment.threshold_met ? 'Met' : 'Not met or unavailable'}</dd></div>
      <div><dt>Recent spatial observations</dt><dd>{assessment.usable_spatial_sources.length} available; {assessment.min_recent_spatial_sources} required</dd></div>
      <div><dt>Maximum observation age</dt><dd>{assessment.max_source_age_minutes} minutes at forecast issue</dd></div>
      <div><dt>Model validation</dt><dd>Synthetic events only</dd></div>
    </dl>
    <div className="research-prose">{assessment.reasons.map(reason => <p key={reason}>{reason}</p>)}</div>
    <p className="panel-footnote">These are explicit policy checks. Observation support is separate from hazard probability and does not measure a universal confidence score.</p>
  </section>;
}
