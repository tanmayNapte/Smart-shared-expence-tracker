class SplitEngine:

    @staticmethod
    def calculate(amount, split_type, participants):

        amount = float(amount)
        splits = {}

        if split_type == "equal":
            count = len(participants)
            share = round(amount / count, 2)

            for uid in participants:
                splits[uid] = share

            diff = round(amount - sum(splits.values()), 2)
            if diff != 0:
                first = list(splits.keys())[0]
                splits[first] += diff

        elif split_type == "percentage":
            total_percent = sum(participants.values())
            if abs(total_percent - 100) > 0.01:
                raise ValueError(f"Percentages must sum to 100 (got {total_percent})")

            for uid, percent in participants.items():
                splits[uid] = round(amount * percent / 100, 2)

        elif split_type == "exact":
            total_exact = sum(participants.values())
            if abs(total_exact - amount) > 0.01:
                raise ValueError(f"Exact split must equal total (got {total_exact}, expected {amount})")

            splits = participants

        elif split_type == "shares":
            total_shares = sum(participants.values())
            if total_shares == 0:
                raise ValueError("Total shares cannot be zero")
            
            one_share = amount / total_shares

            for uid, share in participants.items():
                splits[uid] = round(one_share * share, 2)

        else:
            raise ValueError("Invalid split type")

        return splits
