'''
Created on Mar 29, 2017

@author: ralph
'''

from parser import stpcommands
from ciphers.cipher import AbstractCipher

from parser.stpcommands import getStringRightRotate as rotr
from parser.stpcommands import getStringLeftRotate as rotl

class SPARXRoundCipher(AbstractCipher):
    """
    Represents the differential behaviour of SPARX and can be used
    to find differential characteristics for the given parameters.
    """

    name = "sparxround"
    rounds_per_step = 3

    def getFormatString(self):
        """
        Returns the print format.
        """
        return ['X0', 'X1', 'Y0', 'Y1', 'w']

    def createSTP(self, stp_filename, parameters):
        """
        Creates an STP file to find a characteristic for SPARX with
        the given parameters.
        """

        wordsize = parameters["wordsize"]
        rounds = parameters["rounds"]
        weight = parameters["sweight"]

        with open(stp_filename, 'w') as stp_file:
            header = ("% Input File for STP\n% SPARX w={}"
                      "rounds={}\n\n\n".format(wordsize,rounds))
            stp_file.write(header)

            # Setup variables
            # x0, x1 = left, y0, y1 = right 
            x0 = ["X0{}".format(i) for i in range(rounds + 1)]
            x1 = ["X1{}".format(i) for i in range(rounds + 1)]
            x0_after_A = ["X0A{}".format(i) for i in range(rounds + 1)]
            x1_after_A = ["X1A{}".format(i) for i in range(rounds + 1)]
            x0_after_L = ["X0L{}".format(i) for i in range(rounds + 1)]
            x1_after_L = ["X1L{}".format(i) for i in range(rounds + 1)]
            y0 = ["Y0{}".format(i) for i in range(rounds + 1)]
            y1 = ["Y1{}".format(i) for i in range(rounds + 1)]
            y0_after_A = ["Y0A{}".format(i) for i in range(rounds + 1)]
            y1_after_A = ["Y1A{}".format(i) for i in range(rounds + 1)]

            # w = weight
            w = ["w{}".format(i) for i in range(rounds)]

            stpcommands.setupVariables(stp_file, x0, wordsize)
            stpcommands.setupVariables(stp_file, x1, wordsize)
            stpcommands.setupVariables(stp_file, x0_after_A, wordsize)
            stpcommands.setupVariables(stp_file, x1_after_A, wordsize)
            stpcommands.setupVariables(stp_file, x0_after_L, wordsize)
            stpcommands.setupVariables(stp_file, x1_after_L, wordsize)
            stpcommands.setupVariables(stp_file, y0, wordsize)
            stpcommands.setupVariables(stp_file, y1, wordsize)
            stpcommands.setupVariables(stp_file, y0_after_A, wordsize)
            stpcommands.setupVariables(stp_file, y1_after_A, wordsize)
            stpcommands.setupVariables(stp_file, w, wordsize)

            stpcommands.setupWeightComputation(stp_file, weight, w, wordsize)

            for i in range(rounds):
                self.setupSPARXRound(stp_file, x0[i], x1[i], y0[i], y1[i],
                                     x0_after_A[i], x1_after_A[i],
                                     x0_after_L[i], x1_after_L[i],
                                     y0_after_A[i], y1_after_A[i],
                                     x0[i+1], x1[i+1], y0[i+1], y1[i+1],
                                     w[i], wordsize, rounds)

            # No all zero characteristic
            stpcommands.assertNonZero(stp_file, x0+x1+y0+y1, wordsize)

            # Iterative characteristics only
            # Input difference = Output difference
            if parameters["iterative"]:
                stpcommands.assertVariableValue(stp_file, x0[0], x0[rounds])
                stpcommands.assertVariableValue(stp_file, x1[0], x1[rounds])
                stpcommands.assertVariableValue(stp_file, y0[0], y0[rounds])
                stpcommands.assertVariableValue(stp_file, y1[0], y1[rounds])

            for key, value in parameters["fixedVariables"].items():
                stpcommands.assertVariableValue(stp_file, key, value)

            for char in parameters["blockedCharacteristics"]:
                stpcommands.blockCharacteristic(stp_file, char, wordsize)

            stpcommands.setupQuery(stp_file)

        return

    def setupSPARXRound(self, stp_file, x0_in, x1_in, y0_in, y1_in,
                        x0_after_A, x1_after_A, x0_after_L, x1_after_L,
                        y0_after_A, y1_after_A, x0_out, x1_out, y0_out, y1_out,
                        w, wordsize, rounds):
        """
        Model for differential behaviour of one step SPARX
        """
        command = ""

        # left
        command += self.A(x0_in, x1_in, x0_after_A, x1_after_A, w, wordsize)
        #right
        command += self.A(y0_in, y1_in, y0_after_A, y1_after_A, w, wordsize)

        # every step
        if rounds % self.rounds_per_step:
            command += self.L(x0_after_A, x1_after_A, x0_after_L, x1_after_L)

            #Assert(x_out = L(A^a(x_in)) xor A^a(y_in))
            command += "ASSERT(" + x0_out + " = "
            command += "BVXOR(" + x0_after_L + " , " + y0_after_A + ")"
            command += ");\n"
            command += "ASSERT(" + x1_out + " = "
            command += "BVXOR(" + x1_after_L + " , " + y1_after_A + ")"
            command += ");\n"

            #Assert(y_in = A^a(x_in)
            command += "ASSERT({} = {});\n".format(y0_out, x0_after_A)
            command += "ASSERT({} = {});\n".format(y1_out, x1_after_A)
        else:
            command += "ASSERT({} = {});\n".format(x0_after_A, x0_out)
            command += "ASSERT({} = {});\n".format(x1_after_A, x1_out)
            command += "ASSERT({} = {});\n".format(y0_after_A, y0_out)
            command += "ASSERT({} = {});\n".format(y1_after_A, y1_out)

        stp_file.write(command)
        return


    def A(self, x_in, y_in, x_out, y_out, w, wordsize):
        """
        Model for the ARX box (round) function of SPARX. A^a denotes a 
        rounds of SPECKEY.
        """
        command = ""

        #Assert((x_in >>> 7) + y_in = x_out)
        command += "ASSERT("
        command += stpcommands.getStringAdd(rotr(x_in, 7, wordsize),
                                            y_in, x_out, wordsize)
        command += ");\n"

        #Assert(x_out xor (y_in <<< 2) = y_out)
        command += "ASSERT(" + y_out + " = "
        command += "BVXOR(" + x_out + ","
        command += rotl(y_in, 2, wordsize)
        command += "));\n"

        #For weight computation
        command += "ASSERT({0} = ~".format(w)
        command += stpcommands.getStringEq(rotr(x_in, 7, wordsize),
                                           y_in, x_out)
        command += ");\n"

        return command

    def L(self, x_in, y_in, x_out, y_out):
        """
        Model for the L function in SPARX. L is the Feistel function and 
        is borrowed from NOEKEON.
        """
        command = ""

        # (x_in xor y_in)
        xor_x_y = "BVXOR(" + x_in + " , " + y_in + ")"
        #(x_in xor y_in) <<< 8)
        rot_x_y = rotl(xor_x_y, 8, 16)

        #Assert(x_out = x_in xor ((x_in xor y_in) <<< 8))
        command += "ASSERT(" + x_out + " = "
        command += "BVXOR(" + x_in + " , " + rot_x_y + "));\n"

        #Assert(y_out = y_in xor ((x_in xor y_in) <<< 8))
        command += "ASSERT(" + y_out + " = "
        command += "BVXOR(" + y_in + " , " + rot_x_y + "));\n"

        return command


