"""Close the fresh screen after the retained zero-command name rejection."""
import close_screen
assert close_screen.RUN == 'native-continuation-snapshot-screen-token-01'
close_screen.RUN = 'native-continuation-snapshot-screen-token-02'
if __name__ == '__main__': close_screen.main()
