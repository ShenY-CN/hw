"""Recompute all single-service-area packing and reserve-sensitivity cases."""
from common import Model, save
from solve_transport import q1


def run():
    m = Model()
    for pct in (10, 20, 30, 40):
        save(f'q1_rho{pct}.json', q1(m, pct / 100))
        print('Q1 reserve', pct, flush=True)
    for objective in ('energy', 'time'):
        save(f'q1_{objective}.json', q1(m, .2, objective))
        print('Q1 objective', objective, flush=True)


if __name__ == '__main__':
    run()
