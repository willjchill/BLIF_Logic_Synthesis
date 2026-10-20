from functools import lru_cache


def _covers(pattern: str, term: str) -> bool:
    return all(a == '-' or a == b for a, b in zip(pattern, term))


def _checkTerms(terms: list[str], bitWidth: int) -> set[str]:
    if bitWidth < 1:
        raise ValueError('Number of inputs must be at least 1.')
    for term in terms:
        if len(term) != bitWidth or any(bit not in '01' for bit in term):
            raise ValueError('Minterms must be binary strings matching the input width.')
    return set(terms)


def quineMcCluskey(minterms: list[str], bitWidth: int, dontCares: list[str] = None) -> list[str]:
    onSet = _checkTerms(minterms, bitWidth)
    dcSet = _checkTerms(dontCares or [], bitWidth) - onSet
    if not onSet:
        return []

    current = onSet | dcSet
    primes = set()

    while current:
        combined = set()
        nextGroup = set()
        terms = sorted(current)

        for i in range(len(terms)):
            for j in range(i + 1, len(terms)):
                a, b = terms[i], terms[j]
                differences = [k for k in range(bitWidth) if a[k] != b[k]]
                if len(differences) != 1:
                    continue
                pos = differences[0]
                if a[pos] == '-' or b[pos] == '-':
                    continue

                nextGroup.add(a[:pos] + '-' + a[pos + 1:])
                combined.update((a, b))

        primes.update(current - combined)
        current = nextGroup

    # Ignore implicants that only cover don't-care inputs.
    return sorted((p for p in primes if any(_covers(p, m) for m in onSet)), key=lambda p: p.replace('-', '2'))


def essentialPrimeImplicants(primes: list[str], minterms: list[str]) -> list[str]:
    essentials = set()
    for m in minterms:
        covering = [p for p in primes if _covers(p, m)]
        if len(covering) == 1:
            essentials.add(covering[0])
    return sorted(essentials, key=lambda p: p.replace('-', '2'))


def literalCount(terms: list[str]) -> int:
    return sum(len(term) - term.count('-') for term in terms)


def minimizeSOP(minterms: list[str], bitWidth: int, dontCares: list[str] = None) -> list[str]:
    onSet = sorted(_checkTerms(minterms, bitWidth))
    primes = quineMcCluskey(onSet, bitWidth, dontCares)
    essentials = essentialPrimeImplicants(primes, onSet)
    remaining = [m for m in onSet if not any(_covers(p, m) for p in essentials)]
    if not remaining:
        return essentials

    candidates = [p for p in primes if p not in essentials]
    masks = []
    for p in candidates:
        mask = sum(1 << i for i, m in enumerate(remaining) if _covers(p, m))
        masks.append(mask)

    @lru_cache(None)
    def bestCover(uncovered: int) -> tuple[str, ...]:
        if uncovered == 0:
            return ()

        # Choose the remaining minterm with the fewest possible implicants.
        choices = []
        for i in range(len(remaining)):
            if uncovered & (1 << i):
                options = [j for j, mask in enumerate(masks) if mask & (1 << i)]
                if not choices or len(options) < len(choices):
                    choices = options

        best = None
        for j in choices:
            rest = bestCover(uncovered & ~masks[j])
            solution = tuple(sorted((candidates[j],) + rest))
            if best is None or (literalCount(solution), len(solution), solution) < (literalCount(best), len(best), best):
                best = solution
        return best

    extra = bestCover((1 << len(remaining)) - 1)
    return sorted(essentials + list(extra), key=lambda p: p.replace('-', '2'))


def minimizePOS(maxterms: list[str], bitWidth: int, dontCares: list[str] = None) -> list[str]:
    # Minimize the inverse function, then apply De Morgan's law.
    return minimizeSOP(maxterms, bitWidth, dontCares)
