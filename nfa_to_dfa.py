class NFA:
    def __init__(self, states, alphabet, transitions, start_state, accept_states):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions  # dict: state -> symbol -> set of states
        self.start_state = start_state
        self.accept_states = accept_states

    def epsilon_closure(self, state_set):
        stack = list(state_set)
        closure = set(state_set)
        while stack:
            state = stack.pop()
            if '' in self.transitions.get(state, {}):  # epsilon transitions
                for next_state in self.transitions[state]['']:
                    if next_state not in closure:
                        closure.add(next_state)
                        stack.append(next_state)
        return closure


class DFA:
    def __init__(self, states, alphabet, transitions, start_state, accept_states):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = accept_states

    def accepts(self, string):
        current_state = self.start_state
        for symbol in string:
            if symbol not in self.alphabet:
                return False
            current_state = self.transitions.get(current_state, {}).get(symbol)
            if current_state is None:
                return False
        return current_state in self.accept_states


def nfa_to_dfa(nfa):
    start_closure = frozenset(nfa.epsilon_closure({nfa.start_state}))
    dfa_states = {start_closure}
    unmarked_states = [start_closure]
    dfa_transitions = {}
    dfa_accept_states = set()

    while unmarked_states:
        current = unmarked_states.pop()
        dfa_transitions[current] = {}
        for symbol in nfa.alphabet:
            next_states = set()
            for state in current:
                if symbol in nfa.transitions.get(state, {}):
                    for target in nfa.transitions[state][symbol]:
                        next_states |= nfa.epsilon_closure({target})
            if next_states:
                next_states_frozen = frozenset(next_states)
                dfa_transitions[current][symbol] = next_states_frozen
                if next_states_frozen not in dfa_states:
                    dfa_states.add(next_states_frozen)
                    unmarked_states.append(next_states_frozen)

    for state_set in dfa_states:
        if any(s in nfa.accept_states for s in state_set):
            dfa_accept_states.add(state_set)

    return DFA(
        states=dfa_states,
        alphabet=nfa.alphabet,
        transitions=dfa_transitions,
        start_state=start_closure,
        accept_states=dfa_accept_states
    )


# Example usage
if __name__ == "__main__":
    # Define a simple NFA for regex 'ab*'
    nfa = NFA(
        states={'q0', 'q1', 'q2'},
        alphabet={'a', 'b'},
        transitions={
            'q0': {'a': {'q1'}},
            'q1': {'b': {'q1'}, '': {'q2'}},  # epsilon to q2
        },
        start_state='q0',
        accept_states={'q2'}
    )

    dfa = nfa_to_dfa(nfa)

    test_strings = ["a", "ab", "abb", "b", "aa"]
    for s in test_strings:
        print(f"{s}: {dfa.accepts(s)}")
