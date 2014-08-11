package branching;

public class Branching {

    public Branching() {}

    public int methodWithBranches(int x) {
	if (x > -42)
	    return 2;

	if (x < -145) {
	    if (x == -200)
		return 42;
	    else if (x == -300)
		return 16;
	    else if (x > -189)
		return 7;
	    else
		return 1;
	}

	return 3;
    }
}
