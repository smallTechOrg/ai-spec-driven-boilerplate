import agent.eval_lint


def test_every_ears_line_is_bound():
    # Full mode: every EARS line resolves to a real collectable case AND gate_eval.CRITERION traces to a
    # real P1 EARS line (not the refund placeholder). A green run proves the binding + the prose-vs-prose sync.
    assert agent.eval_lint.main() == 0
