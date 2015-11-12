/*
 * Copyright 2015 Marko Dimjašević
 * 
 * This file is part of JDoop.
 * 
 * JDoop is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * JDoop is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with JDoop.  If not, see <http://www.gnu.org/licenses/>.
*/


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
