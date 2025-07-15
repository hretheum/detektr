#!/usr/bin/env python3
"""
Walidacja macierzy wymagań - sprawdza kompletność i spójność
"""

import pandas as pd
import sys

def validate_requirements_matrix(csv_file):
    """Waliduje macierz wymagań"""
    try:
        # Wczytaj CSV
        df = pd.read_csv(csv_file)
        
        print(f"Loaded {len(df)} requirements from {csv_file}")
        
        # Test 1: Sprawdź wymagane kolumny
        required_columns = ['ID', 'Name', 'Type', 'Priority', 'Component', 'Test_ID', 'Status']
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        else:
            print("✅ All required columns present")
        
        # Test 2: Sprawdź czy Component jest wypełniony
        missing_components = df[df['Component'].isna()].shape[0]
        if missing_components > 0:
            print(f"❌ {missing_components} requirements without Component")
            return False
        else:
            print("✅ All requirements have Component assigned")
        
        # Test 3: Sprawdź czy Test_ID jest wypełniony
        missing_tests = df[df['Test_ID'].isna()].shape[0]
        if missing_tests > 0:
            print(f"❌ {missing_tests} requirements without Test_ID")
            return False
        else:
            print("✅ All requirements have Test_ID assigned")
        
        # Test 4: Sprawdź unikalne ID
        duplicate_ids = df[df.duplicated(subset=['ID'])].shape[0]
        if duplicate_ids > 0:
            print(f"❌ {duplicate_ids} duplicate requirement IDs")
            return False
        else:
            print("✅ All requirement IDs are unique")
        
        # Test 5: Sprawdź poprawne priorytety
        valid_priorities = ['MUST', 'SHOULD', 'COULD', 'WONT']
        invalid_priorities = df[~df['Priority'].isin(valid_priorities)].shape[0]
        if invalid_priorities > 0:
            print(f"❌ {invalid_priorities} requirements with invalid priority")
            return False
        else:
            print("✅ All priorities are valid (MoSCoW)")
        
        # Statystyki
        print("\n📊 Statistics:")
        print(f"   Functional Requirements: {len(df[df['ID'].str.startswith('RF')])}")
        print(f"   Non-functional Requirements: {len(df[df['ID'].str.startswith('RNF')])}")
        print(f"   MUST have: {len(df[df['Priority'] == 'MUST'])}")
        print(f"   SHOULD have: {len(df[df['Priority'] == 'SHOULD'])}")
        print(f"   COULD have: {len(df[df['Priority'] == 'COULD'])}")
        print(f"   WON'T have: {len(df[df['Priority'] == 'WONT'])}")
        
        # Test 6: Coverage check
        components = df['Component'].unique()
        print(f"\n📦 Components covered ({len(components)}):")
        for comp in sorted(components):
            count = len(df[df['Component'] == comp])
            print(f"   - {comp}: {count} requirements")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "requirements-matrix.csv"
    
    if validate_requirements_matrix(csv_file):
        print("\n✅ Requirements matrix validation PASSED")
        sys.exit(0)
    else:
        print("\n❌ Requirements matrix validation FAILED")
        sys.exit(1)