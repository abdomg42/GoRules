import argparse 
from agents.agent import ask
from store import search


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()

    chunks = search(args.project, args.question, top_k=args.top_k)
    answer = ask(args.question, chunks)

    print("\n" + "=" * 60)
    print(answer)
    print("=" * 60)

if __name__ == "__main__":
    main()
