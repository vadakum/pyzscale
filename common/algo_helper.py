# Note: This is not Quantity Finance code, but a utility function for chunking lists.
class AlgoHelper:
    @staticmethod
    def list_chunks(lst, n : int):
        """List generator for n chunks of apporx equal sizes"""
        k, m = divmod(len(lst), n)
        return (lst[i * k + min(i, m): (i + 1) * k + min(i + 1, m)] for i in range(n))


#lst = [1, 2, 3, 4]
#print(list(AlgoHelper.list_chunks(lst, 3)))
