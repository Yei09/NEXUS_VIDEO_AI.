import argparse, json
from nexus_ai.registry import ModelRegistry
from nexus_ai.hardware import snapshot
from nexus_ai.memory import EvolutionMemory

def main():
    parser=argparse.ArgumentParser(prog="nexus-ai"); sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("models"); sub.add_parser("hardware"); sub.add_parser("recover")
    args=parser.parse_args()
    if args.command=="models": result=ModelRegistry().list()
    elif args.command=="hardware": result=snapshot()
    else: result=EvolutionMemory().recover()
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
