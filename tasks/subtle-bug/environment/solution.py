def bsearch(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo < hi:  # bug: drops the final single-element window
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
