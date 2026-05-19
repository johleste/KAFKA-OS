import random
import time


def cmd_python(session, args, bure):
    if not args:
        # Interactive REPL — immediately hangs
        bure.log("PEAD: Python interpreter launch request.")
        bure.simulated_check("Interpreter Sandbox Allocation", "base_check_medium_ms")
        session.write("Python 3.10.12 (main, Nov 20 2023, 15:14:05) [GCC 11.4.0]\n")
        session.write('Type "help", "copyright", "credits" or "license" for more information.\n')
        while True:
            line = session.prompt(">>> ")
            if line in ("exit()", "quit()"):
                break
            bure.log(f"PEAD: Expression '{line[:30]}' submitted for sandbox evaluation.")
            bure.simulated_check("Sandbox Expression Evaluation", "base_check_short_ms")
            bure.log("PEAD: Expression evaluation deferred — sandbox quota exhausted.",
                     level="WARN")
            session.write("# Evaluation deferred: sandbox resource limit reached "
                          f"(Ref: SBX-{bure._short_ref()[:6]})\n")
        return

    script = args[0]
    bure.log(f"PEAD: Python script '{script}' execution requested.")
    bure.simulated_check("Script Static Analysis", "base_check_medium_ms")
    bure.forward('PROC_LAUNCH', f"python:{script}", "Script Execution Request")
    bure.compile_progress(script)


def cmd_python3(session, args, bure):
    cmd_python(session, args, bure)


def cmd_bash(session, args, bure):
    if not args:
        bure.log("PEAD: Sub-shell invocation detected.")
        bure.simulated_check("Sub-shell Authorization", "base_check_medium_ms")
        bure.log("PEAD: Sub-shell denied — nested execution context not permitted "
                 "per Directive EXEC-NEST-3.", level="ERROR")
        session.write("bash: fork: Operation not permitted\n")
        return
    script = args[0]
    bure.log(f"PEAD: Shell script '{script}' execution requested.")
    bure.simulated_check("Shell Script Policy Check", "base_check_medium_ms")
    bure.compile_progress(script)


def cmd_sh(session, args, bure):
    cmd_bash(session, args, bure)


def cmd_gcc(session, args, bure):
    src = next((a for a in args if not a.startswith("-")), "source.c")
    bure.log(f"PEAD: C compilation of '{src}' requested.")
    bure.simulated_check("Compiler License Verification", "base_check_medium_ms")
    bure.forward('PROC_LAUNCH', f"gcc:{src}", "Compilation Request")
    bure.compile_progress(src.replace(".c", ""))


def cmd_make(session, args, bure):
    target = args[0] if args else "all"
    bure.log(f"PEAD: make target '{target}' requested.")
    bure.simulated_check("Build System Authorization", "base_check_medium_ms")
    bure.compile_progress(target)


def cmd_apt(session, args, bure):
    if not args:
        session.write("apt: missing command\n")
        return
    subcmd = args[0]
    pkg = args[1] if len(args) > 1 else "package"
    bure.log(f"PEAD: Package manager operation '{subcmd} {pkg}' requested.")
    bure.simulated_check("Package Repository Policy Validation", "base_check_medium_ms")
    bure.forward('PROC_LAUNCH', f"apt:{subcmd}:{pkg}", "Package Manager Event")

    if subcmd in ("install", "update", "upgrade"):
        session.write(f"Reading package lists... Done\n")
        session.write(f"Building dependency tree... Done\n")
        size_kb = random.randint(200, 5000)
        session.write(f"The following packages will be installed: {pkg} ({size_kb}K)\n")
        session.write(f"Do you want to continue? [Y/n] ")
        confirm = session.prompt("")
        if confirm.lower() not in ("y", "yes", ""):
            session.write("Abort.\n")
            return
        bure.download_progress(f"{pkg}.deb", size_kb)
    else:
        session.write(f"apt: operation '{subcmd}' not permitted without elevated privileges\n")


def cmd_crontab(session, args, bure):
    flags = [a for a in args if a.startswith("-")]
    if "-l" in flags:
        content = session.vfs.read("/etc/crontab")
        if content:
            session.write(content)
        else:
            session.write("no crontab for " + session.username + "\n")
        return

    if "-e" in flags:
        bure.log("PEAD: Crontab edit requested. Launching editor...")
        bure.simulated_check("Cron Job Authorization Pre-check", "base_check_short_ms")
        session.write("# Editing crontab for " + session.username + "\n")
        session.write("# (Enter cron expression. Empty line to cancel)\n")
        job = session.prompt("cron> ")
        if not job:
            session.write("No changes made.\n")
            return
        bure.log(f"PEAD: Cron job '{job[:40]}' submitted for scheduling.")
        bure.simulated_check("Cron Policy Compliance Check", "base_check_medium_ms")
        bure.forward('PROC_LAUNCH', f"crontab:add:{session.username}", "Cron Job Submission")
        ref = bure._short_ref()
        session.write(f"crontab: job scheduled (Ref: CRON-{ref})\n")
        bure.log(f"PEAD: Job logged. Activation pending Cron Authorization Committee review "
                 f"(ETA: 5-10 business days).", level="WARN")
        # Job never actually runs
        return

    if "-r" in flags:
        bure.log("PEAD: Crontab removal requested.")
        bure.simulated_check("Cron Removal Authorization", "base_check_medium_ms")
        session.write(f"crontab: removal pending WOID approval (Ref: WOID-{bure._short_ref()})\n")
